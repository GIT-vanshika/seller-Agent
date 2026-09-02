from decimal import Decimal
from pydantic import ValidationError
from app.contracts import (
    ConversationMessage,
    ConversationState,
    ProductQuestion,
    BuyerIntentDecision,
    AgentActionDecision,
    TrustState,
    NegotiationState,
    TransactionState,
    AgentSession,
)


def run_contract_tests():
    print("==================================================================")
    print("      RUNNING UPDATED BUYER INTENT CONTRACTS TEST SUITE          ")
    print("==================================================================")

    # ------------------------------------------------------------------
    # 1. INTENT & HESITATION DECISION EXAMPLE TESTS (1 to 7)
    # ------------------------------------------------------------------
    # 1. product_question + none
    pq1 = ProductQuestion(question="Is this dress actually pure silk?")
    d1 = BuyerIntentDecision(
        primary_intent="product_question",
        hesitation="none",
        confidence=0.95,
        reason="Buyer asked product fabric question",
        product_question=pq1,
    )
    assert d1.primary_intent == "product_question"
    assert d1.hesitation == "none"
    assert d1.product_question.question == "Is this dress actually pure silk?"
    print("[PASS] Test 1: product_question + none accepted.")

    # 2. trust_concern + trust
    d2 = BuyerIntentDecision(
        primary_intent="trust_concern",
        hesitation="trust",
        confidence=0.90,
        reason="Buyer expressed worry about picture accuracy",
    )
    assert d2.primary_intent == "trust_concern"
    assert d2.hesitation == "trust"
    print("[PASS] Test 2: trust_concern + trust accepted.")

    # 3. price_negotiation + price
    d3 = BuyerIntentDecision(
        primary_intent="price_negotiation",
        hesitation="price",
        confidence=0.92,
        reason="Buyer requested price reduction",
    )
    assert d3.primary_intent == "price_negotiation"
    assert d3.hesitation == "price"
    print("[PASS] Test 3: price_negotiation + price accepted.")

    # 4. both hesitation
    d4 = BuyerIntentDecision(
        primary_intent="trust_concern",
        hesitation="both",
        confidence=0.94,
        reason="Buyer expressed quality worry and price concern",
    )
    assert d4.hesitation == "both"
    print("[PASS] Test 4: both hesitation accepted.")

    # 5. purchase_intent + none
    d5 = BuyerIntentDecision(
        primary_intent="purchase_intent",
        hesitation="none",
        confidence=0.98,
        reason="Buyer expressed direct purchase commitment",
    )
    assert d5.primary_intent == "purchase_intent"
    assert d5.hesitation == "none"
    print("[PASS] Test 5: purchase_intent + none accepted.")

    # 6. clarification + none
    d6 = BuyerIntentDecision(
        primary_intent="clarification",
        hesitation="none",
        confidence=0.88,
        reason="Buyer asked for sizing clarification",
    )
    assert d6.primary_intent == "clarification"
    assert d6.hesitation == "none"
    print("[PASS] Test 6: clarification + none accepted.")

    # 7. general_conversation + none
    d7 = BuyerIntentDecision(
        primary_intent="general_conversation",
        hesitation="none",
        confidence=0.95,
        reason="General politeness / greeting",
    )
    assert d7.primary_intent == "general_conversation"
    assert d7.hesitation == "none"
    print("[PASS] Test 7: general_conversation + none accepted.")

    # ------------------------------------------------------------------
    # 2. VALIDATION & SECURITY TESTS (8 to 19)
    # ------------------------------------------------------------------
    # 8. invalid primary_intent rejected
    try:
        BuyerIntentDecision(
            primary_intent="unknown_intent_type",
            hesitation="none",
            confidence=0.9,
            reason="Invalid",
        )
        assert False, "Invalid primary_intent should be rejected"
    except ValidationError:
        print("[PASS] Test 8: Invalid primary_intent correctly rejected.")

    # 9. invalid hesitation rejected
    try:
        BuyerIntentDecision(
            primary_intent="trust_concern",
            hesitation="unknown_hesitation",
            confidence=0.9,
            reason="Invalid",
        )
        assert False, "Invalid hesitation should be rejected"
    except ValidationError:
        print("[PASS] Test 9: Invalid hesitation correctly rejected.")

    # 10. confidence < 0 rejected
    try:
        BuyerIntentDecision(
            primary_intent="trust_concern",
            hesitation="trust",
            confidence=-0.1,
            reason="Negative confidence",
        )
        assert False, "Confidence < 0 should be rejected"
    except ValidationError:
        print("[PASS] Test 10: Confidence < 0.0 correctly rejected.")

    # 11. confidence > 1 rejected
    try:
        BuyerIntentDecision(
            primary_intent="trust_concern",
            hesitation="trust",
            confidence=1.1,
            reason="Over confidence",
        )
        assert False, "Confidence > 1 should be rejected"
    except ValidationError:
        print("[PASS] Test 11: Confidence > 1.0 correctly rejected.")

    # 12. empty reason rejected
    try:
        BuyerIntentDecision(
            primary_intent="trust_concern",
            hesitation="trust",
            confidence=0.9,
            reason="",
        )
        assert False, "Empty reason should be rejected"
    except ValidationError:
        print("[PASS] Test 12: Empty reason correctly rejected.")

    # 13. empty product question rejected
    try:
        ProductQuestion(question="")
        assert False, "Empty question in ProductQuestion should be rejected"
    except ValidationError:
        print("[PASS] Test 13: Empty product question correctly rejected.")

    # 14. extra price field rejected
    try:
        BuyerIntentDecision(
            primary_intent="price_negotiation",
            hesitation="price",
            confidence=0.9,
            reason="Negotiation",
            price=Decimal("1500.00"),
        )
        assert False, "Extra price field should be rejected"
    except ValidationError:
        print("[PASS] Test 14: Extra price field in BuyerIntentDecision strictly rejected.")

    # 15. extra reservation_price rejected
    try:
        BuyerIntentDecision(
            primary_intent="price_negotiation",
            hesitation="price",
            confidence=0.9,
            reason="Negotiation",
            reservation_price=Decimal("1550.00"),
        )
        assert False, "Extra reservation_price field should be rejected"
    except ValidationError:
        print("[PASS] Test 15: Extra reservation_price field strictly rejected.")

    # 16. extra target_price rejected
    try:
        BuyerIntentDecision(
            primary_intent="price_negotiation",
            hesitation="price",
            confidence=0.9,
            reason="Negotiation",
            target_price=Decimal("1750.00"),
        )
        assert False, "Extra target_price field should be rejected"
    except ValidationError:
        print("[PASS] Test 16: Extra target_price field strictly rejected.")

    # 17. extra arbitrary tool field rejected
    try:
        BuyerIntentDecision(
            primary_intent="product_question",
            hesitation="none",
            confidence=0.9,
            reason="Question",
            execute_tool="fetch_private_key",
        )
        assert False, "Extra arbitrary tool field should be rejected"
    except ValidationError:
        print("[PASS] Test 17: Extra arbitrary tool field strictly rejected.")

    # 18. AgentActionDecision cannot contain financial authorization fields
    try:
        AgentActionDecision(action="negotiate_price", reason="Valid", create_order=True)
        assert False, "Financial authorization field should be rejected in AgentActionDecision"
    except ValidationError:
        print("[PASS] Test 18: Financial authorization field strictly rejected in AgentActionDecision.")

    # 19. AgentActionDecision cannot contain arbitrary tool execution instructions
    try:
        AgentActionDecision(action="provide_information", reason="Valid", tool="search_db")
        assert False, "Arbitrary tool execution instruction should be rejected"
    except ValidationError:
        print("[PASS] Test 19: Arbitrary tool execution instruction strictly rejected in AgentActionDecision.")

    # ------------------------------------------------------------------
    # 3. COMPOSITE AGENT SESSION & CONVERSATION TESTS
    # ------------------------------------------------------------------
    msg1 = ConversationMessage(role="user", content="What fabric is this made from?")
    msg2 = ConversationMessage(role="assistant", content="This dress is handcrafted from 100% Mulberry Silk.")
    conv = ConversationState(session_id="sess_intent_01", product_id="prod_003", messages=[msg1, msg2])

    sess = AgentSession(
        session_id="sess_intent_01",
        product_id="prod_003",
        conversation=conv,
        intent_decision=d1,
        action_decision=AgentActionDecision(action="provide_information", reason="Answer product fabric question"),
        trust=TrustState(status="resolved", last_evidence_ids_used=["ev_001"]),
        negotiation=NegotiationState(active=False),
        transaction=TransactionState(status="not_ready"),
        created_at="2026-08-30T17:00:00Z",
        updated_at="2026-08-30T17:00:00Z",
    )

    dump_data = sess.model_dump(mode="json")
    for kw in ["reservation_price", "target_price", "aspiration_price", "batna", "execute_tool"]:
        assert kw not in dump_data, f"SECURITY VIOLATION: Forbidden key {kw} found in AgentSession!"

    print("[PASS] Test 20: AgentSession composite model verified zero private parameters & zero tool leakage.")

    print("\n==================================================================")
    print("   [SUCCESS] ALL BUYER INTENT CONTRACT & SECURITY TESTS PASSED 100%!")
    print("==================================================================\n")


if __name__ == "__main__":
    run_contract_tests()
