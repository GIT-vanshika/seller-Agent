import os
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.data_loader import db
from app.models import Product, SellerPolicy, Evidence
from app.intent_classifier import IntentClassifier, IntentResult
from app.gemini_intent_service import GeminiIntentService, PublicProductContext, GeminiSalespersonService
from app.contracts import BuyerIntentDecision, TrustState, BuyerSafeCommercialContext, UpsellOpportunity
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
        client_override_salesperson: Optional[Any] = None,
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

        # Session Context Awareness
        in_negotiation = session.negotiation_round > 0 or session.deal_status in ["negotiating", "agreed"]

        # 4. Intent Understanding: Deterministic-first pre-check to conserve Gemini quota and avoid 429 errors
        is_unambiguous, fast_decision = IntentClassifier.is_unambiguous_intent(user_text, in_negotiation=in_negotiation)
        if client_override_intent is not None or not is_unambiguous or fast_decision is None:
            intent_decision: BuyerIntentDecision = GeminiIntentService.understand_buyer_intent(
                message=user_text,
                conversation_context=history_snippet,
                product_context=public_context,
                client_override=client_override_intent,
            )
        else:
            intent_decision = fast_decision

        session.latest_intent_decision = intent_decision

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
        is_deliberation = IntentClassifier.is_deliberation(user_text)
        is_savings = IntentClassifier.is_savings_query(user_text)
        is_product_q = IntentClassifier.is_product_question(user_text)

        # Resolve entities: Gemini Stage 1 or deterministic regex fallback
        extracted_qty = intent_decision.requested_quantity if intent_decision.requested_quantity is not None else intent_res.requested_quantity
        requested_qty = extracted_qty if extracted_qty is not None else session.quantity
        offered_price = intent_decision.offered_price if intent_decision.offered_price is not None else intent_res.offered_price

        # DETERMINISTIC INTENT RESOLUTION:
        primary = intent_decision.primary_intent
        hesitation = intent_decision.hesitation

        if is_deliberation:
            primary = "deliberation"
            hesitation = "none"
        elif is_savings:
            primary = "savings_inquiry"
            hesitation = "none"
        # Natural acceptance phrases or payment inquiries map directly to purchase_intent
        elif is_acceptance_phrase or is_payment_inquiry or intent_res.intent == "checkout_intent":
            primary = "purchase_intent"
            hesitation = "none"
        elif is_product_q and offered_price is None:
            primary = "product_question"
            hesitation = "trust"
        elif primary in ["quantity_pricing_query", "seller_policy_probing"]:
            hesitation = "price"
        elif intent_decision.confidence == 0.0 and intent_res.intent != "general_inquiry":
            # Deterministic fallback when Gemini is unavailable
            primary = intent_res.intent
            if primary in ["price_hesitation", "bulk_request"]:
                hesitation = "price"
            elif primary in ["trust_hesitation", "trust_concern"]:
                hesitation = "trust"
        elif in_negotiation and (intent_res.offered_price is not None or intent_res.requested_quantity is not None or intent_decision.offered_price is not None or intent_decision.requested_quantity is not None) and primary not in ["product_question", "trust_concern"]:
            # If in an active negotiation and user sends a price offer or changes quantity, preserve negotiation flow
            primary = "price_negotiation"
            hesitation = "price"

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

            # Separate Product Details from Media Requests
            media_intent = IntentClassifier.classify_media_intent(user_text)
            if media_intent == "PRODUCT_PHOTO":
                evidence_dicts = [
                    {"id": e.id, "type": e.type, "source": e.source, "label": e.label, "content": e.content}
                    for e in retrieved_evidence if e.type == "image"
                ]
            elif media_intent == "PRODUCT_VIDEO":
                evidence_dicts = [
                    {"id": e.id, "type": e.type, "source": e.source, "label": e.label, "content": e.content}
                    for e in retrieved_evidence if e.type == "video"
                ]
            elif media_intent == "PRODUCT_PHOTO_VIDEO":
                evidence_dicts = [
                    {"id": e.id, "type": e.type, "source": e.source, "label": e.label, "content": e.content}
                    for e in retrieved_evidence if e.type in ["image", "video"]
                ]
            else:
                evidence_dicts = []

            # Baseline deal validation: preserve active validated deal if matching quantity
            if session.last_validated_deal and session.last_validated_deal.is_valid and session.last_validated_deal.quantity == session.quantity:
                validated_deal = session.last_validated_deal
            else:
                single_anchor = session.single_unit_negotiated_price or (session.current_negotiated_unit_price if session.quantity == 1 else None)
                val_req = DealValidationRequest(
                    product_id=product_id,
                    quantity=session.quantity,
                    proposed_unit_price=session.current_negotiated_unit_price or product.listed_price,
                    seller_authorized_price=session.current_negotiated_unit_price or product.listed_price,
                    current_negotiated_unit_price=single_anchor,
                    negotiation_round=session.negotiation_round,
                )
                validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)

        # --- B. PRICE NEGOTIATION AGENT FLOW ---
        elif primary in ["price_negotiation", "price_hesitation", "bulk_request", "quantity_pricing_query", "seller_policy_probing"] or hesitation in ["price", "both"] or offered_price is not None:
            current_round = session.negotiation_round + 1
            
            max_rounds = policy.max_negotiation_rounds

            # Cleanly handle price evaluation:
            # If buyer made a specific price offer, evaluate against it.
            # If buyer switched quantity or inquired without an offer, evaluate cleanly for requested_qty.
            if offered_price is not None:
                eval_price = offered_price
            else:
                eval_price = None

            # Determine negotiated anchor to pass
            negotiated_anchor = session.single_unit_negotiated_price or session.current_negotiated_unit_price

            # B1. Deterministic PolicyEngine Concession Evaluation
            decision: PolicyEngineDecision = PolicyEngine.evaluate_offer(
                policy=policy,
                buyer_offer=eval_price,
                round_number=current_round,
                quantity=requested_qty,
                negotiated_unit_price=negotiated_anchor,
            )

            # B2. Deterministic DealConsistencyValidator Final Authority
            proposed_eval_price = eval_price if eval_price is not None else decision.seller_authorized_price
            val_req = DealValidationRequest(
                product_id=product_id,
                quantity=requested_qty,
                proposed_unit_price=proposed_eval_price,
                seller_authorized_price=decision.seller_authorized_price,
                current_negotiated_unit_price=negotiated_anchor,
                negotiation_round=current_round,
                buyer_committed=False,
            )

            validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
            # In Flow B (negotiation / counter / policy probing):
            # A deal is ONLY accepted if the buyer explicitly proposed an acceptable price (eval_price is not None and decision.accepted).
            # Negotiation round exhaustion or inquiries without an acceptable price offer NEVER trigger acceptance.
            is_deal_accepted = bool(decision.accepted and validated_deal.is_valid and eval_price is not None)

            # Update Session State
            session = session_db.record_negotiation_step(
                session_id=session.session_id,
                agreed_price=validated_deal.effective_unit_price if is_deal_accepted else None,
                quantity=requested_qty,
                increment_round=(policy.pricing_mode != "fixed"),
            )
            # Establish the authoritative counter / firm price in session
            session.current_negotiated_unit_price = validated_deal.effective_unit_price
            if requested_qty == 1:
                session.single_unit_negotiated_price = validated_deal.effective_unit_price
            session = session_db.set_validated_deal(
                session.session_id,
                validated_deal,
                is_agreed=is_deal_accepted,
            )

            # Reusable Commercial Engine: Dynamic Upsell Calculation
            upsell_opp: Optional[UpsellOpportunity] = None
            if policy.bulk_rules and policy.bulk_rules.tiers:
                higher_tiers = [t for t in policy.bulk_rules.tiers if t.min_quantity > requested_qty]
                if higher_tiers:
                    next_tier = min(higher_tiers, key=lambda t: t.min_quantity)
                    # REUSE commercial engine: evaluate_offer for the next tier
                    upsell_eval = PolicyEngine.evaluate_offer(
                        policy=policy,
                        buyer_offer=None,
                        round_number=current_round,
                        quantity=next_tier.min_quantity,
                        negotiated_unit_price=negotiated_anchor,
                    )
                    if upsell_eval.seller_authorized_price < validated_deal.effective_unit_price:
                        upsell_total = (upsell_eval.seller_authorized_price * Decimal(str(next_tier.min_quantity))).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        upsell_opp = UpsellOpportunity(
                            min_quantity=next_tier.min_quantity,
                            unit_rate=upsell_eval.seller_authorized_price,
                            total_payable=upsell_total,
                            discount_pct=upsell_eval.applied_tier_discount if not upsell_eval.is_floor_clamped else None,
                        )

            # B3. Grounded Response Generation
            if policy.pricing_mode == "fixed":
                response_text = (
                    f"{product.name} is offered under a fixed pricing model at ₹{product.listed_price:.2f}/unit. "
                    f"Discounts are not available for single units. Total for {requested_qty} unit(s) is ₹{validated_deal.total_payable_amount:.2f}."
                )
                can_show_payment = False
            elif is_deal_accepted:
                session.deal_status = "agreed"
                status_val = "agreed"
                can_show_payment = True

                commercial_ctx = BuyerSafeCommercialContext(
                    product_name=product.name,
                    catalog_listed_price=product.listed_price,
                    single_unit_negotiated_anchor=session.single_unit_negotiated_price,
                    requested_quantity=requested_qty,
                    effective_unit_price=validated_deal.effective_unit_price,
                    total_payable_amount=validated_deal.total_payable_amount,
                    applied_discount_percentage=decision.applied_tier_discount if not decision.is_floor_clamped else None,
                    is_floor_clamped=decision.is_floor_clamped,
                    negotiation_round=current_round,
                    max_rounds=max_rounds,
                    is_final_round=False,
                    deal_status=status_val,
                    buyer_accepted=True,
                    can_show_payment=True,
                    upsell_opportunity=upsell_opp,
                )
                response_text = GeminiSalespersonService.generate_salesperson_response(
                    message=user_text,
                    commercial_context=commercial_ctx,
                    chat_history=history_snippet,
                    client_override=client_override_salesperson,
                    buyer_intent=primary,
                )
            else:
                is_final = (current_round >= max_rounds)
                session.deal_status = "negotiating"
                status_val = "firm_policy_boundary" if is_final else "negotiating"
                can_show_payment = False

                commercial_ctx = BuyerSafeCommercialContext(
                    product_name=product.name,
                    catalog_listed_price=product.listed_price,
                    single_unit_negotiated_anchor=session.single_unit_negotiated_price,
                    requested_quantity=requested_qty,
                    effective_unit_price=validated_deal.effective_unit_price,
                    total_payable_amount=validated_deal.total_payable_amount,
                    applied_discount_percentage=decision.applied_tier_discount if not decision.is_floor_clamped else None,
                    is_floor_clamped=decision.is_floor_clamped,
                    negotiation_round=current_round,
                    max_rounds=max_rounds,
                    is_final_round=is_final,
                    deal_status=status_val,
                    buyer_accepted=is_deal_accepted,
                    can_show_payment=can_show_payment,
                    upsell_opportunity=upsell_opp,
                )

                response_text = GeminiSalespersonService.generate_salesperson_response(
                    message=user_text,
                    commercial_context=commercial_ctx,
                    chat_history=history_snippet,
                    client_override=client_override_salesperson,
                    buyer_intent=primary,
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
                negotiated_anchor = session.single_unit_negotiated_price or (session.current_negotiated_unit_price if session.quantity == 1 else None)
                if session.last_validated_deal and session.last_validated_deal.quantity == requested_qty:
                    eval_price = session.last_validated_deal.effective_unit_price
                else:
                    eval_price = session.current_negotiated_unit_price or negotiated_anchor or product.listed_price

                val_req = DealValidationRequest(
                    product_id=product_id,
                    quantity=requested_qty,
                    proposed_unit_price=eval_price,
                    seller_authorized_price=eval_price,
                    current_negotiated_unit_price=negotiated_anchor,
                    negotiation_round=session.negotiation_round,
                    buyer_committed=True,
                )
                validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
                session = session_db.set_validated_deal(session.session_id, validated_deal, is_agreed=validated_deal.is_valid)
                can_show_payment = validated_deal.is_valid

                if validated_deal.is_valid:
                    session.deal_status = "agreed"
                    session.quantity = requested_qty
                    session.current_negotiated_unit_price = validated_deal.effective_unit_price
                    commercial_ctx = BuyerSafeCommercialContext(
                        product_name=product.name,
                        catalog_listed_price=product.listed_price,
                        single_unit_negotiated_anchor=session.single_unit_negotiated_price,
                        requested_quantity=requested_qty,
                        effective_unit_price=validated_deal.effective_unit_price,
                        total_payable_amount=validated_deal.total_payable_amount,
                        applied_discount_percentage=None,
                        is_floor_clamped=False,
                        negotiation_round=session.negotiation_round,
                        max_rounds=policy.max_negotiation_rounds,
                        is_final_round=False,
                        deal_status="agreed",
                        buyer_accepted=True,
                        can_show_payment=True,
                        upsell_opportunity=None,
                    )
                    response_text = GeminiSalespersonService.generate_salesperson_response(
                        message=user_text,
                        commercial_context=commercial_ctx,
                        chat_history=history_snippet,
                        client_override=client_override_salesperson,
                        buyer_intent=primary,
                    )
                else:
                    response_text = f"Unable to validate deal for checkout: {validated_deal.validation_message}"

        # --- S. SAVINGS INQUIRY FLOW ---
        elif primary == "savings_inquiry":
            active_qty = session.quantity
            if session.last_validated_deal and session.last_validated_deal.quantity == active_qty:
                validated_deal = session.last_validated_deal
            else:
                single_anchor = session.single_unit_negotiated_price or (session.current_negotiated_unit_price if session.quantity == 1 else None)
                val_req = DealValidationRequest(
                    product_id=product_id,
                    quantity=active_qty,
                    proposed_unit_price=session.current_negotiated_unit_price or product.listed_price,
                    seller_authorized_price=session.current_negotiated_unit_price or product.listed_price,
                    current_negotiated_unit_price=single_anchor,
                    negotiation_round=session.negotiation_round,
                )
                validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
                session = session_db.set_validated_deal(session.session_id, validated_deal, is_agreed=False)

            active_unit = validated_deal.effective_unit_price
            active_total = validated_deal.total_payable_amount
            single_anchor = session.single_unit_negotiated_price or product.listed_price
            normal_total = (single_anchor * Decimal(str(active_qty))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            catalog_total = (product.listed_price * Decimal(str(active_qty))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            savings_vs_anchor = (normal_total - active_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            savings_vs_catalog = (catalog_total - active_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if session.single_unit_negotiated_price and session.single_unit_negotiated_price < product.listed_price:
                response_text = (
                    f"At your negotiated rate of ₹{single_anchor:,.2f} each, {active_qty} pieces would normally come to ₹{normal_total:,.2f}. "
                    f"With our 18% volume discount applied, you pay ₹{active_unit:,.2f} per piece, totaling ₹{active_total:,.2f} — "
                    f"so you save ₹{savings_vs_anchor:,.2f} compared with buying {active_qty} at your negotiated rate "
                    f"(and ₹{savings_vs_catalog:,.2f} off the original catalog price)! If that works for you, let me know."
                )
            else:
                response_text = (
                    f"At the standard listed price of ₹{product.listed_price:,.2f} each, {active_qty} pieces would normally come to ₹{catalog_total:,.2f}. "
                    f"With our bulk discount applied, you pay ₹{active_unit:,.2f} per piece, totaling ₹{active_total:,.2f} — "
                    f"so you save ₹{savings_vs_catalog:,.2f} in total! If that works for you, let me know."
                )

            can_show_payment = False
            session.deal_status = "negotiating"

        # --- D. CLARIFICATION & GENERAL CONVERSATION FLOW ---
        else:
            can_show_payment = False
            if in_negotiation:
                session.deal_status = "negotiating"

            # Check if this message was actually a product inquiry that reached Flow D
            if IntentClassifier.is_product_question(user_text) and offered_price is None:
                retrieved_evidence, assessment = EvidenceRetriever.retrieve_evidence_for_product(
                    product_id=product_id, question=user_text
                )
                response_text = ProductQAService.answer_product_question(
                    product=product,
                    evidence_list=retrieved_evidence,
                    assessment=assessment,
                    buyer_question=user_text,
                )
                session.trust_state = TrustState(
                    status=assessment.status,
                    last_evidence_ids_used=assessment.evidence_ids_used,
                )
                validated_deal = session.last_validated_deal
            else:
                # Clarification / General Conversation
                # PRESERVE existing validated deal if matching quantity
                if session.last_validated_deal and session.last_validated_deal.is_valid and session.last_validated_deal.quantity == session.quantity:
                    validated_deal = session.last_validated_deal
                else:
                    single_anchor = session.single_unit_negotiated_price or (session.current_negotiated_unit_price if session.quantity == 1 else None)
                    val_req = DealValidationRequest(
                        product_id=product_id,
                        quantity=session.quantity,
                        proposed_unit_price=session.current_negotiated_unit_price or product.listed_price,
                        seller_authorized_price=session.current_negotiated_unit_price or product.listed_price,
                        current_negotiated_unit_price=single_anchor,
                        negotiation_round=session.negotiation_round,
                    )
                    validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
                    session = session_db.set_validated_deal(session.session_id, validated_deal, is_agreed=False)

                commercial_status = session.deal_status if session.deal_status in ["agreed", "firm_policy_boundary", "checked_out"] else "negotiating"
                commercial_ctx = BuyerSafeCommercialContext(
                    product_name=product.name,
                    catalog_listed_price=product.listed_price,
                    single_unit_negotiated_anchor=session.single_unit_negotiated_price,
                    requested_quantity=session.quantity,
                    effective_unit_price=validated_deal.effective_unit_price if validated_deal else (session.current_negotiated_unit_price or product.listed_price),
                    total_payable_amount=validated_deal.total_payable_amount if validated_deal else Decimal("0.00"),
                    applied_discount_percentage=None,
                    is_floor_clamped=False,
                    negotiation_round=session.negotiation_round,
                    max_rounds=policy.max_negotiation_rounds,
                    is_final_round=session.negotiation_round >= policy.max_negotiation_rounds,
                    deal_status=commercial_status,
                    buyer_accepted=False,
                    can_show_payment=False,
                    upsell_opportunity=None,
                )

                # Generate natural response via Stage 3 salesperson (or safe deterministic fallback)
                response_text = GeminiSalespersonService.generate_salesperson_response(
                    message=user_text,
                    commercial_context=commercial_ctx,
                    chat_history=history_snippet,
                    client_override=client_override_salesperson,
                    buyer_intent=primary,
                )

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
