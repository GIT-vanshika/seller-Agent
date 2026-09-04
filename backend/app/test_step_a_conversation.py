from decimal import Decimal
from app.orchestrator import AgentOrchestrator
from app.session_manager import session_db


def run_step_a_tests():
    print("==================================================================")
    print("      RUNNING STEP A CONVERSATION & NEGOTIATION SUITE             ")
    print("==================================================================")

    # -------------------------------------------------------------------------
    # TEST 1: Acceptance WITHOUT an active deal must NOT manufacture a deal
    # -------------------------------------------------------------------------
    sess_fresh = "sess_fresh_acceptance"
    res1 = AgentOrchestrator.process_user_message(sess_fresh, "prod_003", "Ok done")
    assert res1.validated_deal is None, "ERROR: Manufactured a deal without negotiation!"
    assert "haven't agreed on a deal yet" in res1.message or "haven't discussed a deal yet" in res1.message
    print("[PASS] Test 1: Acceptance phrase without active counter-offer does NOT manufacture a deal.")

    res1_deal = AgentOrchestrator.process_user_message("sess_fresh_deal", "prod_003", "Deal")
    assert res1_deal.validated_deal is None, "ERROR: Manufactured a deal for 'Deal' without negotiation!"
    print("[PASS] Test 1b: 'Deal' without active negotiation does NOT manufacture a deal.")

    # -------------------------------------------------------------------------
    # TEST 2: Numeric Non-Offers must NOT become price negotiation
    # -------------------------------------------------------------------------
    sess_q = "sess_numeric_questions"
    for q in [
        "What sizes are available in 3 colors?",
        "Does it come in 3 sizes?",
        "How many pieces are available?",
        "What is the warranty period?",
    ]:
        res_q = AgentOrchestrator.process_user_message(sess_q, "prod_003", q)
        assert res_q.intent != "price_hesitation", f"ERROR: '{q}' falsely became price_hesitation!"
        assert res_q.negotiation_round == 0, f"ERROR: '{q}' incremented negotiation round!"
    print("[PASS] Test 2: Questions with numbers (3 colors, 3 sizes) correctly preserved as non-price inquiries.")

    # -------------------------------------------------------------------------
    # TEST 3: Multi-turn Natural Negotiation Continuation
    # -------------------------------------------------------------------------
    sess_neg = "sess_multi_turn_neg"

    # Turn 1: Initial negotiation
    t1 = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "Can I get it under 1900?")
    assert t1.intent in ["price_negotiation", "price_hesitation"], f"Turn 1 intent: {t1.intent}"
    assert t1.negotiation_round == 1
    assert t1.validated_deal is not None
    counter_1 = t1.validated_deal.effective_unit_price
    print(f"[PASS] Test 3.1: Turn 1 'under 1900' -> Round {t1.negotiation_round}, Counter: Rs.{counter_1}")

    # Turn 2: 'Ok 1800'
    t2 = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "Ok 1800")
    assert t2.intent in ["price_negotiation", "price_hesitation"], f"Turn 2 intent: {t2.intent}"
    assert t2.negotiation_round == 2
    assert "I am here to assist with your purchase" not in t2.message, "Fell into generic clarification!"
    counter_2 = t2.validated_deal.effective_unit_price
    assert counter_2 < counter_1, "Counter offer did not concede"
    print(f"[PASS] Test 3.2: Turn 2 'Ok 1800' -> Round {t2.negotiation_round}, Counter: Rs.{counter_2}")

    # Turn 3: 'ok Then 1700?'
    t3 = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "ok Then 1700?")
    assert t3.intent in ["price_negotiation", "price_hesitation"], f"Turn 3 intent: {t3.intent}"
    assert t3.negotiation_round == 3
    assert "I am here to assist with your purchase" not in t3.message
    counter_3 = t3.validated_deal.effective_unit_price
    print(f"[PASS] Test 3.3: Turn 3 'ok Then 1700?' -> Round {t3.negotiation_round}, Counter: Rs.{counter_3}")

    # Turn 4: 'I want it 1750 final'
    t4 = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "I want it 1750 final")
    assert t4.intent in ["price_negotiation", "price_hesitation"], f"Turn 4 intent: {t4.intent}"
    assert t4.negotiation_round == 4
    assert "I am here to assist with your purchase" not in t4.message
    counter_4 = t4.validated_deal.effective_unit_price
    print(f"[PASS] Test 3.4: Turn 4 'I want it 1750 final' -> Round {t4.negotiation_round}, Counter: Rs.{counter_4}")

    # Turn 5: 'How about 1700?'
    t5 = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "How about 1700?")
    assert t5.intent in ["price_negotiation", "price_hesitation"], f"Turn 5 intent: {t5.intent}"
    assert t5.negotiation_round == 5
    counter_5 = t5.validated_deal.effective_unit_price
    print(f"[PASS] Test 3.5: Turn 5 'How about 1700?' -> Round {t5.negotiation_round}, Counter: Rs.{counter_5}")

    # Turn 6: Product question mid-negotiation does NOT reset round or prices
    t_q = AgentOrchestrator.process_user_message(sess_neg, "prod_003", "What material is this?")
    assert t_q.intent not in ["price_negotiation", "price_hesitation"]
    session_after_q = session_db.get_session(sess_neg)
    assert session_after_q.negotiation_round == 5
    assert session_after_q.current_negotiated_unit_price == counter_5
    print(f"[PASS] Test 3.6: Product question mid-negotiation answered without losing negotiation state.")

    # Turn 7: '1800' directly proposes a price
    sess_direct = "sess_direct_num"
    AgentOrchestrator.process_user_message(sess_direct, "prod_003", "Can I get under 1900?")
    t_direct = AgentOrchestrator.process_user_message(sess_direct, "prod_003", "1800")
    assert t_direct.intent in ["price_negotiation", "price_hesitation"]
    assert t_direct.negotiation_round == 2
    print(f"[PASS] Test 3.7: Standalone '1800' in active negotiation recognized as price offer.")

    # Turn 8: 'I'll pay 1750' and '1800 is my final offer'
    sess_phrases = "sess_phrases"
    AgentOrchestrator.process_user_message(sess_phrases, "prod_003", "Can you do a discount?")
    t_pay = AgentOrchestrator.process_user_message(sess_phrases, "prod_003", "I'll pay 1750")
    assert t_pay.intent in ["price_negotiation", "price_hesitation"]
    t_final = AgentOrchestrator.process_user_message(sess_phrases, "prod_003", "1800 is my final offer")
    assert t_final.intent in ["price_negotiation", "price_hesitation"]
    print(f"[PASS] Test 3.8: 'I\\'ll pay 1750' and '1800 is my final offer' successfully evaluated.")

    # -------------------------------------------------------------------------
    # TEST 4: State-Aware Acceptance with Active Counter-Offer
    # -------------------------------------------------------------------------
    # Accepting after active counter
    acceptance_phrases = [
        "Ok done",
        "Done",
        "Deal",
        "Agreed",
        "I'll take it",
        "I’ll take it",
        "Take it",
        "Yes, let's do it",
        "Let's do it",
        "Okay, I'll take it",
    ]

    for phrase in acceptance_phrases:
        sid = f"sess_acc_{hash(phrase)}"
        # Start negotiation
        AgentOrchestrator.process_user_message(sid, "prod_003", "Can I get for 1800?")
        # Now accept
        res_acc = AgentOrchestrator.process_user_message(sid, "prod_003", phrase)
        assert res_acc.intent == "purchase_intent", f"Failed for '{phrase}', intent was {res_acc.intent}"
        assert res_acc.validated_deal is not None, f"Deal was None for '{phrase}'"
        assert res_acc.validated_deal.is_valid is True, f"Deal was invalid for '{phrase}'"
        assert res_acc.validated_deal.effective_unit_price == Decimal("2400.00"), f"Price mismatch for '{phrase}'"
        assert res_acc.validated_deal.effective_unit_price == Decimal("2425.00"), f"Price mismatch for '{phrase}'"
        assert "Deal confirmed" in res_acc.message or "locked" in res_acc.message

    print(f"[PASS] Test 4: All {len(acceptance_phrases)} natural acceptance phrases correctly accept active counter-offer.")

    # -------------------------------------------------------------------------
    # TEST 5: Cross-Product Isolation
    # -------------------------------------------------------------------------
    sess_iso = "sess_iso_test"
    AgentOrchestrator.process_user_message(sess_iso, "prod_003", "Can I get for 1800?")
    iso_p3 = session_db.get_session(sess_iso)
    assert iso_p3.negotiation_round == 1
    assert iso_p3.current_negotiated_unit_price == Decimal("2400.00")
    assert iso_p3.current_negotiated_unit_price == Decimal("2425.00")

    # Switch to prod_001 (cookies, fixed price 100)
    AgentOrchestrator.process_user_message(sess_iso, "prod_001", "Hello")
    iso_p1 = session_db.get_session(sess_iso)
    assert iso_p1.product_id == "prod_001"
    assert iso_p1.negotiation_round == 0
    assert iso_p1.current_negotiated_unit_price is None
    print("[PASS] Test 5: Cross-product isolation verified: switching product cleanly resets negotiation state.")

    # -------------------------------------------------------------------------
    # TEST 6: Trust and Product Questions Preservation
    # -------------------------------------------------------------------------
    sess_trust = "sess_trust_test"
    t_trust = AgentOrchestrator.process_user_message(sess_trust, "prod_003", "Are these pictures real?")
    assert t_trust.intent in ["trust_hesitation", "trust_concern"]
    assert len(t_trust.evidence_items) > 0

    t_silk = AgentOrchestrator.process_user_message(sess_trust, "prod_003", "Is the material actually silk?")
    assert t_silk.intent in ["trust_concern", "trust_hesitation", "product_question"]

    t_care = AgentOrchestrator.process_user_message(sess_trust, "prod_003", "How do I care for it?")
    assert t_care.intent in ["product_question", "trust_concern", "trust_hesitation"]
    print("[PASS] Test 6: Trust questions and care questions accurately classified and handled.")

    print("\n==================================================================")
    print("   [SUCCESS] ALL STEP A CONVERSATION & NEGOTIATION TESTS PASSED!   ")
    print("==================================================================\n")


if __name__ == "__main__":
    run_step_a_tests()
