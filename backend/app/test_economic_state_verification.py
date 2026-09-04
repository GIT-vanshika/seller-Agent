from decimal import Decimal
from app.orchestrator import AgentOrchestrator
from app.session_manager import session_db


def test_economic_and_acceptance():
    print("==================================================")
    print("      EXACT ECONOMIC STATE & ACCEPTANCE PASS      ")
    print("==================================================")

    # 1. Start active negotiation
    sid = "sess_economic_state_test"
    pid = "prod_003"
    r1 = AgentOrchestrator.process_user_message(sid, pid, "Can I get under 1900")
    r2 = AgentOrchestrator.process_user_message(sid, pid, "Ok 1800")
    
    # Session state BEFORE acceptance
    s_before = session_db.get_session(sid)
    deal_before = s_before.last_validated_deal
    print("\n--- STATE BEFORE ACCEPTANCE ---")
    print(f"negotiation_round: {s_before.negotiation_round}")
    print(f"current_negotiated_unit_price: Rs.{s_before.current_negotiated_unit_price}")
    print(f"deal.is_valid: {deal_before.is_valid if deal_before else None}")
    print(f"deal_status: {s_before.deal_status}")
    print(f"checkout_eligible: {deal_before.is_valid if deal_before else False}")

    assert s_before.negotiation_round == 2
    assert s_before.current_negotiated_unit_price == Decimal("2350.00")
    assert s_before.deal_status == "negotiating"
    assert deal_before.is_valid is False  # Counter-offer is pending, not yet accepted by buyer

    # 2. Send "Ok done" to accept active counter
    r3 = AgentOrchestrator.process_user_message(sid, pid, "Ok done")
    s_after = session_db.get_session(sid)
    deal_after = s_after.last_validated_deal
    print("\n--- STATE AFTER 'Ok done' ---")
    print(f"negotiation_round: {s_after.negotiation_round}")
    print(f"deal_status: {s_after.deal_status}")
    print(f"effective_unit_price: Rs.{deal_after.effective_unit_price}")
    print(f"deal.is_valid: {deal_after.is_valid}")
    print(f"validated_deal_id: {deal_after.deal_id}")
    print(f"checkout_eligible: {deal_after.is_valid}")
    print(f"applied_rule_description: {deal_after.applied_rule_description}")

    assert s_after.negotiation_round == 2  # Acceptance does not consume a new concession round
    assert s_after.deal_status == "agreed"
    assert deal_after.is_valid is True
    assert deal_after.effective_unit_price == Decimal("2350.00")
    assert deal_after.deal_id.startswith("deal_")

    # 3. Test "Deal", "I'll take it", "Agreed" during active negotiations
    for phrase in ["Deal", "I'll take it", "Agreed"]:
        slug = phrase.replace(' ', '_').replace("'", "")
        test_sid = f"sess_acc_test_{slug}"
        AgentOrchestrator.process_user_message(test_sid, pid, "Can I get under 1800")
        res_phrase = AgentOrchestrator.process_user_message(test_sid, pid, phrase)
        assert res_phrase.validated_deal is not None
        assert res_phrase.validated_deal.is_valid is True
        assert res_phrase.deal_status == "agreed"
        print(f"[PASS] Active acceptance via '{phrase}' -> deal.is_valid=True, deal_status=agreed, price=Rs.{res_phrase.validated_deal.effective_unit_price}")

    # 4. Zero seller-private policy leak verification
    exported = session_db.export_agent_session(sid)
    exp_json = exported.model_dump_json()
    for secret in ["reservation_price", "target_price", "aspiration_price", "batna"]:
        assert secret not in exp_json, f"LEAK DETECTED: {secret} found in exported session!"
    print("[PASS] Security boundary verified: Zero seller-private policy secrets in session state.")

    print("\n==================================================")
    print("  [SUCCESS] ECONOMIC STATE & ACCEPTANCE VERIFIED! ")
    print("==================================================")

if __name__ == "__main__":
    test_economic_and_acceptance()
