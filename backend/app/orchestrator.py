import os
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.data_loader import db
from app.models import Product, SellerPolicy, Evidence
from app.intent_classifier import IntentClassifier, IntentResult
from app.gemini_intent_service import GeminiIntentService, PublicProductContext
from app.contracts import BuyerIntentDecision, TrustState
from app.policy_engine import PolicyEngine, PolicyEngineDecision
from app.deal_validator import DealConsistencyValidator, ValidatedDeal, DealValidationRequest
from app.session_manager import session_db, SessionState, ChatMessage
from app.evidence_retriever import EvidenceRetriever, EvidenceAssessment
from app.product_qa_service import ProductQAService
from app.audit_logger import audit_logger


class AgentChatResponse(BaseModel):
    session_id: str
    product_id: str
    message: str
    intent: str
    deal_status: str
    negotiation_round: int
    quantity: int
    current_negotiated_unit_price: Optional[Decimal] = None
    validated_deal: Optional[ValidatedDeal] = None
    evidence_items: List[Dict[str, Any]] = []


class AgentOrchestrator:
    """
    Agent Orchestrator conforming to Frozen Architecture:
    Buyer Chat -> Conversation Manager -> Gemini Intent Understanding -> Agent Orchestrator ->
    (Product Q&A / Trust Agent | Negotiation Agent) -> Decision -> Final Deal Validator
    """

    @classmethod
    def process_user_message(
        cls,
        session_id: Optional[str],
        product_id: str,
        user_text: str,
        client_override_intent: Optional[Any] = None,
    ) -> AgentChatResponse:
        # 1. Fetch catalog product data and private seller policy
        product: Optional[Product] = db.get_product(product_id)
        policy: Optional[SellerPolicy] = db.get_seller_policy(product_id)

        if not product or not policy:
            raise ValueError(f"Product {product_id} or policy not found")

        # 2. Get / create bounded session state & append user message
        session: SessionState = session_db.get_or_create_session(session_id, product_id)
        session_db.append_message(session.session_id, sender="buyer", text=user_text)

        # 3. Extract public product context (ZERO SellerPolicy leakage)
        public_context = PublicProductContext(
            product_id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            listed_price=float(product.listed_price),
            tags=[],
        )

        # Prepare chat history snippet (last 3 messages)
        history_snippet = [
            {"role": "user" if m.sender == "buyer" else "assistant", "content": m.text}
            for m in session.messages[-4:-1]
        ]

        # 4. Invoke Gemini Intent Understanding Intelligence Layer
        intent_decision: BuyerIntentDecision = GeminiIntentService.understand_buyer_intent(
            message=user_text,
            conversation_context=history_snippet,
            product_context=public_context,
            client_override=client_override_intent,
        )
        session.latest_intent_decision = intent_decision

        # Extract numeric offers or quantity from IntentClassifier fallback regex helper
        intent_res: IntentResult = IntentClassifier.classify(user_text)

        # DETERMINISTIC FALLBACK RESOLUTION:
        # If Gemini returned fallback decision (confidence 0.0), resolve intent via IntentClassifier
        primary = intent_decision.primary_intent
        hesitation = intent_decision.hesitation
        if intent_decision.confidence == 0.0 and intent_res.intent != "general_inquiry":
            primary = intent_res.intent
            if primary in ["price_hesitation", "bulk_request"]:
                hesitation = "price"
            elif primary in ["trust_hesitation", "trust_concern"]:
                hesitation = "trust"

        requested_qty = intent_res.requested_quantity or session.quantity
        offered_price = intent_res.offered_price

        response_text = ""
        validated_deal: Optional[ValidatedDeal] = None
        evidence_dicts: List[Dict[str, Any]] = []

        # 5. Route by Intent & Hesitation Classification

        # --- A. PRODUCT Q&A / TRUST AGENT FLOW ---
        if (primary in ["product_question", "trust_concern"] or hesitation in ["trust", "both"]) and offered_price is None:
            # A1. Retrieve Evidence & Provenance Assessment
            retrieved_evidence, assessment = EvidenceRetriever.retrieve_evidence_for_product(
                product_id=product_id, question=user_text
            )

            # A2. Formulate Grounded Response
            response_text = ProductQAService.answer_product_question(
                product=product,
                evidence_list=retrieved_evidence,
                assessment=assessment,
                buyer_question=user_text,
            )

            # A3. Update TrustState
            session.trust_state = TrustState(
                status=assessment.status,
                last_evidence_ids_used=assessment.evidence_ids_used,
            )

            evidence_dicts = [
                {"id": e.id, "type": e.type, "source": e.source, "label": e.label, "content": e.content}
                for e in retrieved_evidence
            ]

            # Baseline deal validation
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=session.quantity,
                proposed_unit_price=session.current_negotiated_unit_price or product.listed_price,
                seller_authorized_price=session.current_negotiated_unit_price or product.listed_price,
                current_negotiated_unit_price=session.current_negotiated_unit_price,
                negotiation_round=session.negotiation_round,
            )
            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)

        # --- B. PRICE NEGOTIATION AGENT FLOW ---
        elif primary == "price_negotiation" or hesitation in ["price", "both"] or offered_price is not None:
            current_round = session.negotiation_round + 1
            eval_price = offered_price or (session.current_negotiated_unit_price or (product.listed_price * Decimal("0.90")))

            # B1. Deterministic PolicyEngine Concession Evaluation
            decision: PolicyEngineDecision = PolicyEngine.evaluate_offer(
                policy=policy,
                buyer_offer=eval_price,
                round_number=current_round,
                quantity=requested_qty,
            )

            # B2. Deterministic DealConsistencyValidator Final Authority
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=requested_qty,
                proposed_unit_price=eval_price,
                seller_authorized_price=decision.seller_authorized_price,
                current_negotiated_unit_price=session.current_negotiated_unit_price,
                negotiation_round=current_round,
                buyer_committed=False,
            )

            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
            is_deal_accepted = decision.accepted and validated_deal.is_valid

            # Update Session State
            session = session_db.record_negotiation_step(
                session_id=session.session_id,
                agreed_price=validated_deal.effective_unit_price if is_deal_accepted else None,
                quantity=requested_qty,
                increment_round=True,
            )
            session = session_db.set_validated_deal(session.session_id, validated_deal)

            # B3. Grounded Counter-Offer Response Generation
            if policy.pricing_mode == "fixed":
                response_text = (
                    f"{product.name} is offered under a fixed pricing model at ₹{product.listed_price:.2f}/unit. "
                    f"Discounts are not available for single units. Total for {requested_qty} unit(s) is ₹{validated_deal.total_payable_amount:.2f}."
                )
            elif is_deal_accepted:
                response_text = (
                    f"Great news! Your offer/requested terms for {product.name} have been approved.\n"
                    f"• Effective Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                    f"• Quantity: {validated_deal.quantity}\n"
                    f"• Total Payable Amount: ₹{validated_deal.total_payable_amount:.2f}\n"
                    f"({validated_deal.applied_rule_description})\n\n"
                    f"Click 'Proceed to Checkout' below to lock in this validated deal."
                )
            else:
                if validated_deal.validation_code == "EXCEEDED_MAX_ROUNDS":
                    response_text = (
                        f"We have reached the maximum negotiation rounds for this item. "
                        f"Our final firm deal is ₹{validated_deal.effective_unit_price:.2f} per unit "
                        f"(Total: ₹{validated_deal.total_payable_amount:.2f} for {requested_qty} unit(s))."
                    )
                else:
                    response_text = (
                        f"Your offer of ₹{eval_price:.2f} is below our acceptable commercial range for {product.name}. "
                        f"Our counter-offer for this round is ₹{validated_deal.effective_unit_price:.2f} per unit "
                        f"(Total: ₹{validated_deal.total_payable_amount:.2f} for {requested_qty} unit(s))."
                    )

        # --- C. PURCHASE INTENT FLOW ---
        elif primary == "purchase_intent":
            eval_price = session.current_negotiated_unit_price or product.listed_price
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=requested_qty,
                proposed_unit_price=eval_price,
                seller_authorized_price=eval_price,
                current_negotiated_unit_price=session.current_negotiated_unit_price,
                negotiation_round=session.negotiation_round,
                buyer_committed=True,
            )
            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
            session = session_db.set_validated_deal(session.session_id, validated_deal)

            if validated_deal.is_valid:
                response_text = (
                    f"Your deal for {product.name} is validated and locked!\n"
                    f"• Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                    f"• Quantity: {validated_deal.quantity}\n"
                    f"• Total Amount: ₹{validated_deal.total_payable_amount:.2f}\n\n"
                    f"Ready to complete checkout with Razorpay."
                )
            else:
                response_text = f"Unable to validate deal for checkout: {validated_deal.validation_message}"

        # --- D. CLARIFICATION & GENERAL CONVERSATION FLOW ---
        else:
            response_text = (
                f"Welcome! I am your AI Purchase Confidence & Deal Agent for {product.name}.\n"
                f"Listed price is ₹{product.listed_price:.2f}. "
                f"Feel free to ask about product quality evidence or negotiate commercial terms."
            )
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=session.quantity,
                proposed_unit_price=session.current_negotiated_unit_price or product.listed_price,
                seller_authorized_price=session.current_negotiated_unit_price or product.listed_price,
                current_negotiated_unit_price=session.current_negotiated_unit_price,
                negotiation_round=session.negotiation_round,
            )
            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)

        # 6. Append agent response to session
        session_db.append_message(
            session_id=session.session_id,
            sender="agent",
            text=response_text,
            intent=primary,
            suggested_price=validated_deal.effective_unit_price if validated_deal else None,
        )

        # 7. Audit Logging (Zero private policy field leakage)
        audit_logger.log_event(
            event_type="chat_turn_processed",
            session_id=session.session_id,
            product_id=product_id,
            data={
                "user_text": user_text,
                "intent": primary,
                "hesitation": hesitation,
                "confidence": intent_decision.confidence,
                "negotiation_round": session.negotiation_round,
                "quantity": session.quantity,
                "validated_deal": validated_deal.model_dump(mode="json") if validated_deal else None,
            },
        )

        return AgentChatResponse(
            session_id=session.session_id,
            product_id=product_id,
            message=response_text,
            intent=primary,
            deal_status=session.deal_status,
            negotiation_round=session.negotiation_round,
            quantity=session.quantity,
            current_negotiated_unit_price=session.current_negotiated_unit_price,
            validated_deal=validated_deal,
            evidence_items=evidence_dicts,
        )
