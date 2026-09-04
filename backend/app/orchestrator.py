import os
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
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
    can_show_payment: bool = False


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

        # Session Context Awareness
        in_negotiation = session.negotiation_round > 0 or session.deal_status in ["negotiating", "agreed"]

        # Extract numeric offers or quantity from IntentClassifier fallback regex helper with context
        intent_res: IntentResult = IntentClassifier.classify(
            user_text,
            in_negotiation=in_negotiation,
            current_negotiated_price=session.current_negotiated_unit_price,
            listed_price=product.listed_price,
        )

        is_acceptance_phrase = IntentClassifier.is_acceptance(user_text)
        is_payment_inquiry = IntentClassifier.is_payment_inquiry(user_text)
        is_explicit_buy = IntentClassifier.is_explicit_buy(user_text)

        # DETERMINISTIC INTENT RESOLUTION:
        primary = intent_decision.primary_intent
        hesitation = intent_decision.hesitation

        # Natural acceptance phrases or payment inquiries map directly to purchase_intent
        if is_acceptance_phrase or is_payment_inquiry or intent_res.intent == "checkout_intent":
            primary = "purchase_intent"
            hesitation = "none"
        elif intent_decision.confidence == 0.0 and intent_res.intent != "general_inquiry":
            # Deterministic fallback when Gemini is unavailable
            primary = intent_res.intent
            if primary in ["price_hesitation", "bulk_request"]:
                hesitation = "price"
            elif primary in ["trust_hesitation", "trust_concern"]:
                hesitation = "trust"
        elif in_negotiation and (intent_res.offered_price is not None or intent_res.requested_quantity is not None) and primary not in ["product_question", "trust_concern"]:
            # If in an active negotiation and user sends a price offer or changes quantity, preserve negotiation flow
            primary = "price_negotiation"
            hesitation = "price"

        requested_qty = intent_res.requested_quantity if intent_res.requested_quantity is not None else session.quantity
        offered_price = intent_res.offered_price

        response_text = ""
        validated_deal: Optional[ValidatedDeal] = None
        evidence_dicts: List[Dict[str, Any]] = []
        can_show_payment: bool = False

        # 5. Route by Intent & Hesitation Classification

        # --- A. PRODUCT Q&A / TRUST AGENT FLOW ---
        if (primary in ["product_question", "trust_concern", "trust_hesitation"] or hesitation in ["trust", "both"]) and offered_price is None:
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
        elif primary in ["price_negotiation", "price_hesitation", "bulk_request"] or hesitation in ["price", "both"] or offered_price is not None:
            current_round = session.negotiation_round + 1
            
            max_rounds = policy.max_negotiation_rounds

            # Cleanly handle price evaluation:
            # If buyer made a specific price offer, evaluate against it.
            # If buyer switched quantity or inquired without an offer, evaluate cleanly for requested_qty.
            if offered_price is not None:
                eval_price = offered_price
            elif requested_qty != session.quantity:
                eval_price = None
            else:
                eval_price = session.current_negotiated_unit_price

            # B1. Deterministic PolicyEngine Concession Evaluation
            decision: PolicyEngineDecision = PolicyEngine.evaluate_offer(
                policy=policy,
                buyer_offer=eval_price,
                round_number=current_round,
                quantity=requested_qty,
            )

            # B2. Deterministic DealConsistencyValidator Final Authority
            # Pass proposed_unit_price if buyer offered one; otherwise authorized price for this quantity
            proposed_eval_price = eval_price if eval_price is not None else decision.seller_authorized_price
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=requested_qty,
                proposed_unit_price=proposed_eval_price,
                seller_authorized_price=decision.seller_authorized_price,
                current_negotiated_unit_price=session.current_negotiated_unit_price if requested_qty == session.quantity else None,
                negotiation_round=current_round,
                buyer_committed=False,
            )

            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
            is_deal_accepted = decision.accepted and validated_deal.is_valid

            # Update Session State
            session = session_db.record_negotiation_step(
                session_id=session.session_id,
                agreed_price=validated_deal.effective_unit_price if (is_deal_accepted and current_round < max_rounds) else None,
                quantity=requested_qty,
                increment_round=(policy.pricing_mode != "fixed"),
            )
            # Establish the authoritative counter / firm price in session
            session.current_negotiated_unit_price = validated_deal.effective_unit_price
            session = session_db.set_validated_deal(
                session.session_id,
                validated_deal,
                is_agreed=is_deal_accepted and (current_round < max_rounds),
            )

            # B3. Grounded Counter-Offer Response Generation
            if policy.pricing_mode == "fixed":
                response_text = (
                    f"{product.name} is offered under a fixed pricing model at ₹{product.listed_price:.2f}/unit. "
                    f"Discounts are not available for single units. Total for {requested_qty} unit(s) is ₹{validated_deal.total_payable_amount:.2f}."
                )
                can_show_payment = False
            elif current_round >= max_rounds:
                # NEGOTIATION FINISHED != BUYER ACCEPTED.
                # When round reaches the seller's final firm price:
                # - Establish the final authoritative seller price
                # - Tell the buyer: "We cannot get below ₹X. It is against seller policy."
                # - Do not use "maximum rounds exceeded" or "limit" language.
                # - Do not automatically manufacture buyer acceptance merely because round was reached.
                # - Do not mark the deal as buyer-agreed solely because negotiation ended.
                session.deal_status = "negotiating"
                can_show_payment = False
                final_price = validated_deal.effective_unit_price
                total_amt = (final_price * requested_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                response_text = (
                    f"We cannot get below ₹{final_price:.2f}. It is against seller policy.\n\n"
                    f"Our final firm price for {product.name} is ₹{final_price:.2f} per unit "
                    f"(Total: ₹{total_amt:.2f} for {requested_qty} unit(s)).\n\n"
                    f"If you would like to proceed with this purchase, reply 'Ok done' or 'I want to buy', or ask where to pay."
                )
            elif is_deal_accepted:
                # Seller accepts buyer's offer, but buyer has not yet given explicit purchase commitment
                can_show_payment = False
                response_text = (
                    f"Great news! Your offer for {product.name} has been approved.\n"
                    f"• Effective Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                    f"• Quantity: {validated_deal.quantity}\n"
                    f"• Total Payable Amount: ₹{validated_deal.total_payable_amount:.2f}\n"
                    f"({validated_deal.applied_rule_description})\n\n"
                    f"To complete your purchase, reply 'Ok done' or 'I want to buy', or ask where to pay!"
                )
            else:
                can_show_payment = False
                if offered_price is not None:
                    response_text = (
                        f"Your offer of ₹{offered_price:.2f} is below our acceptable commercial range for {product.name}. "
                        f"Our counter-offer is ₹{validated_deal.effective_unit_price:.2f} per unit "
                        f"(Total: ₹{validated_deal.total_payable_amount:.2f} for {requested_qty} unit(s))."
                    )
                else:
                    response_text = (
                        f"For {requested_qty} unit(s) of {product.name}, our authorized price is ₹{validated_deal.effective_unit_price:.2f} per unit "
                        f"(Total: ₹{validated_deal.total_payable_amount:.2f})."
                    )

        # --- C. PURCHASE INTENT FLOW ---
        elif primary == "purchase_intent":
            has_active_counter = (
                session.negotiation_round > 0 and
                (session.current_negotiated_unit_price is not None or
                 (session.last_validated_deal is not None and session.last_validated_deal.effective_unit_price is not None))
            )

            # State-Aware Acceptance Guard:
            # If buyer sends a bare acceptance token ("Ok done", "Deal", "Agreed")
            # WITHOUT an active negotiation counter-offer on a negotiable product,
            # do NOT manufacture a price or deal.
            if is_acceptance_phrase and not has_active_counter and not is_explicit_buy and policy.pricing_mode == "negotiable":
                response_text = (
                    f"We haven't agreed on a deal yet for {product.name}. "
                    f"The listed MRP is ₹{product.listed_price:.2f}. "
                    f"Would you like to purchase at this listed price, or propose a price offer?"
                )
                validated_deal = None
                can_show_payment = False
            else:
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
                session = session_db.set_validated_deal(session.session_id, validated_deal, is_agreed=validated_deal.is_valid)
                can_show_payment = validated_deal.is_valid

                if validated_deal.is_valid:
                    if is_payment_inquiry:
                        response_text = (
                            f"Deal confirmed! You have accepted our offer for {product.name}.\n"
                            f"You can pay for it securely right below using our official Razorpay checkout gateway!\n\n"
                            f"• Effective Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                            f"• Quantity: {validated_deal.quantity} unit(s)\n"
                            f"• Total Payable Amount: ₹{validated_deal.total_payable_amount:.2f}\n\n"
                            f"Click 'Pay with Razorpay' below to complete your payment."
                        )
                    elif has_active_counter:
                        response_text = (
                            f"Deal confirmed! You have accepted our offer for {product.name}.\n\n"
                            f"• Effective Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                            f"• Quantity: {validated_deal.quantity} unit(s)\n"
                            f"• Total Payable Amount: ₹{validated_deal.total_payable_amount:.2f}\n"
                            f"({validated_deal.applied_rule_description})\n\n"
                            f"Click 'Proceed to Checkout' below to lock in this validated deal."
                            f"Click 'Pay with Razorpay' below to lock in this validated deal."
                        )
                    else:
                        response_text = (
                            f"Your deal for {product.name} is validated and locked at the listed price!\n"
                            f"Your purchase for {product.name} is confirmed and locked at the catalog listed price!\n\n"
                            f"• Unit Price: ₹{validated_deal.effective_unit_price:.2f}\n"
                            f"• Quantity: {validated_deal.quantity}\n"
                            f"• Quantity: {validated_deal.quantity} unit(s)\n"
                            f"• Total Amount: ₹{validated_deal.total_payable_amount:.2f}\n\n"
                            f"Ready to complete checkout with Razorpay."
                            f"Ready to complete checkout with Razorpay below."
                        )
                else:
                    response_text = f"Unable to validate deal for checkout: {validated_deal.validation_message}"

        # --- D. CLARIFICATION & GENERAL CONVERSATION FLOW ---
        else:
            if len(session.messages) <= 2:
                response_text = (
                    f"Welcome! I am your AI Purchase Confidence & Deal Agent for {product.name}.\n"
                    f"Listed price is ₹{product.listed_price:.2f}. "
                    f"Feel free to ask about product quality evidence or negotiate commercial terms."
                )
            else:
                response_text = (
                    f"I am here to assist with your purchase of {product.name}. "
                    f"Listed MRP is ₹{product.listed_price:.2f}. You can ask about product specs, quality evidence, or propose a price offer."
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
                "can_show_payment": can_show_payment,
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
            can_show_payment=can_show_payment,
        )
