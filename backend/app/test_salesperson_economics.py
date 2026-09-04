from decimal import Decimal
from app.data_loader import db
from app.policy_engine import PolicyEngine
from app.deal_validator import DealConsistencyValidator, DealValidationRequest
from app.orchestrator import AgentOrchestrator
from app.session_manager import session_db


def test_salesperson_economics():
    print("==================================================")
    print("     TESTING SALESPERSON-STYLE NEGOTIATION        ")
    print("==================================================")

    policy_003 = db.get_seller_policy("prod_003")
    assert policy_003 is not None
    assert policy_003.listed_price == Decimal("2500.00")
    assert policy_003.target_price == Decimal("2050.00")
    assert policy_003.reservation_price == Decimal("1550.00")

    # ----------------------------------------------------
    # TEST 1: Direct PolicyEngine 5-Round Concession Curve
    # TEST 1: Direct PolicyEngine 7-Round Concession Curve
    # ----------------------------------------------------
    expected_curve = [
        Decimal("2400.00"),
        Decimal("2325.00"),
        Decimal("2250.00"),
        Decimal("2425.00"),
        Decimal("2350.00"),
        Decimal("2275.00"),
        Decimal("2200.00"),
        Decimal("2150.00"),
        Decimal("2100.00"),
        Decimal("2050.00"),
    ]
    prev_price = policy_003.listed_price
    for r in range(1, 6):
    for r in range(1, 8):
        dec = PolicyEngine.evaluate_offer(policy_003, buyer_offer=Decimal("1500.00"), round_number=r, quantity=1)
        expected = expected_curve[r - 1]
        assert dec.seller_authorized_price == expected, f"Round {r} expected {expected}, got {dec.seller_authorized_price}"
        drop = prev_price - dec.seller_authorized_price
        print(f"[PASS] Round {r}: Counter Rs.{dec.seller_authorized_price} (concession: Rs.{drop:.2f})")
        prev_price = dec.seller_authorized_price

    # Verify slow early concession, meaningful later concessions
    r1_drop = policy_003.listed_price - expected_curve[0]  # 100
    r4_drop = expected_curve[2] - expected_curve[3]        # 100
    r5_drop = expected_curve[3] - expected_curve[4]        # 100
    r1_drop = policy_003.listed_price - expected_curve[0]  # 75
    assert r1_drop <= Decimal("100.00"), f"R1 concession too large: {r1_drop}"
    assert r1_drop < (policy_003.listed_price - policy_003.target_price) * Decimal("0.30"), "R1 consumed too much margin!"
    print("[PASS] Concession pacing verified: R1 concession (Rs.100) protects 78% of negotiable margin.")
    print("[PASS] Concession pacing verified: R1 concession (Rs.75) protects 83% of negotiable margin.")

    # ----------------------------------------------------
    # TEST 2: Quantity Incentives
    # ----------------------------------------------------
    q1 = PolicyEngine.evaluate_offer(policy_003, buyer_offer=Decimal("1500.00"), round_number=1, quantity=1)
    q2 = PolicyEngine.evaluate_offer(policy_003, buyer_offer=Decimal("1500.00"), round_number=1, quantity=2)
    q3 = PolicyEngine.evaluate_offer(policy_003, buyer_offer=Decimal("1500.00"), round_number=1, quantity=3)

    assert q1.seller_authorized_price == Decimal("2400.00")
    assert q1.seller_authorized_price == Decimal("2425.00")
    assert q2.seller_authorized_price == Decimal("2125.00")
    assert q3.seller_authorized_price == Decimal("2050.00")

    # Monotonicity checks
    assert q1.seller_authorized_price >= q2.seller_authorized_price >= q3.seller_authorized_price >= policy_003.reservation_price
    print("[PASS] Quantity incentives verified: 1 pc = Rs.2400, 2 pcs = Rs.2125/unit, 3 pcs = Rs.2050/unit.")
    print("[PASS] Quantity incentives verified: 1 pc = Rs.2425, 2 pcs = Rs.2125/unit, 3 pcs = Rs.2050/unit.")

    # ----------------------------------------------------
    # TEST 3: Multi-turn Natural Progression (Lowball Flow)
    # ----------------------------------------------------
    sid_lowball = "sess_salesperson_lowball"
    turns = [
        ("Can I get it under 1900?", Decimal("2400.00"), 1),
        ("Ok 1800", Decimal("2325.00"), 2),
        ("How about 1700?", Decimal("2250.00"), 3),
        ("1750 final", Decimal("2150.00"), 4),
        ("1700 final", Decimal("2050.00"), 5),
        ("Can I get it under 1900?", Decimal("2425.00"), 1),
        ("Ok 1800", Decimal("2350.00"), 2),
        ("How about 1700?", Decimal("2275.00"), 3),
        ("1750 final", Decimal("2200.00"), 4),
        ("1700 final", Decimal("2150.00"), 5),
        ("1650 final", Decimal("2100.00"), 6),
        ("1600 final", Decimal("2050.00"), 7),
    ]
    for msg, exp_price, exp_round in turns:
        res = AgentOrchestrator.process_user_message(sid_lowball, "prod_003", msg)
        assert res.negotiation_round == exp_round
        assert res.validated_deal.effective_unit_price == exp_price, f"Expected {exp_price}, got {res.validated_deal.effective_unit_price}"
        assert res.deal_status == "negotiating"
    print("[PASS] Lowball offers did not cause early capitulation; strictly followed salesperson schedule.")

    # ----------------------------------------------------
    # TEST 4: Premature Acceptance Guard (Gentle Offers)
    # ----------------------------------------------------
    sid_gentle = "sess_salesperson_gentle"
    g1 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "Can I get it for 2400?")
    assert g1.deal_status == "agreed" and g1.validated_deal.effective_unit_price == Decimal("2400.00")
    g1 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "Can I get it for 2425?")
    assert g1.deal_status == "agreed" and g1.validated_deal.effective_unit_price == Decimal("2425.00")

    g2 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "2300?")
    assert g2.deal_status == "negotiating" and g2.validated_deal.effective_unit_price == Decimal("2325.00")
    assert g2.deal_status == "negotiating" and g2.validated_deal.effective_unit_price == Decimal("2350.00")

    g3 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "2200?")
    assert g3.deal_status == "negotiating" and g3.validated_deal.effective_unit_price == Decimal("2250.00")
    assert g3.deal_status == "negotiating" and g3.validated_deal.effective_unit_price == Decimal("2275.00")

    g4 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "2100?")
    assert g4.deal_status == "negotiating" and g4.validated_deal.effective_unit_price == Decimal("2150.00")
    assert g4.deal_status == "negotiating" and g4.validated_deal.effective_unit_price == Decimal("2200.00")

    g5 = AgentOrchestrator.process_user_message(sid_gentle, "prod_003", "2050?")
    assert g5.deal_status == "agreed" and g5.validated_deal.effective_unit_price == Decimal("2050.00")
    assert g5.deal_status == "negotiating" and g5.validated_deal.effective_unit_price == Decimal("2150.00")
    print("[PASS] Gentle offers verified: final authorized price was NOT given away prematurely.")

    # ----------------------------------------------------
    # TEST 5: Quantity Switching & Isolation (Scenarios D & E)
    # ----------------------------------------------------
    sid_switch = "sess_quantity_switch"
    # Turn 1: 1 unit
    d1 = AgentOrchestrator.process_user_message(sid_switch, "prod_003", "Can I get 1 for 1900?")
    assert d1.validated_deal.quantity == 1 and d1.validated_deal.effective_unit_price == Decimal("2400.00")
    assert d1.validated_deal.quantity == 1 and d1.validated_deal.effective_unit_price == Decimal("2425.00")

    # Turn 2: switch to 2 units
    d2 = AgentOrchestrator.process_user_message(sid_switch, "prod_003", "Can you do better if I take 2?")
    assert d2.validated_deal.quantity == 2 and d2.validated_deal.effective_unit_price == Decimal("2125.00")

    # Turn 3: switch to 3 units
    d3 = AgentOrchestrator.process_user_message(sid_switch, "prod_003", "What about 3?")
    assert d3.validated_deal.quantity == 3 and d3.validated_deal.effective_unit_price == Decimal("2050.00")

    # Turn 4: switch BACK to 1 unit (MUST NOT LEAK 2050)
    d4 = AgentOrchestrator.process_user_message(sid_switch, "prod_003", "1 piece")
    assert d4.validated_deal.quantity == 1
    assert d4.validated_deal.effective_unit_price == Decimal("2150.00") or d4.validated_deal.effective_unit_price > Decimal("2050.00")
    assert d4.validated_deal.effective_unit_price == Decimal("2200.00") or d4.validated_deal.effective_unit_price > Decimal("2050.00")
    print("[PASS] Quantity switching verified: Zero leakage of 3-piece discount back to 1 piece.")

    # ----------------------------------------------------
    # TEST 6: Floor Security Enforcement
    # ----------------------------------------------------
    req_sub_floor = DealValidationRequest(
        product_id="prod_003",
        quantity=1,
        proposed_unit_price=Decimal("1200.00"),
        seller_authorized_price=Decimal("1200.00"),  # Attempted unauthorized override below reservation
        negotiation_round=1,
    )
    val_floor = DealConsistencyValidator.validate_deal(policy_003, req_sub_floor)
    assert not val_floor.is_valid
    assert val_floor.validation_code == "EXCEEDS_RESERVATION_FLOOR"
    print("[PASS] Reservation floor strictly enforced: Unauthorized price below floor rejected.")

    # ----------------------------------------------------
    # TEST 7: Cross-Product Isolation
    # ----------------------------------------------------
    sid_iso = "sess_cross_product_iso"
    iso_p3 = AgentOrchestrator.process_user_message(sid_iso, "prod_003", "Can I get under 1900?")
    assert iso_p3.validated_deal.product_id == "prod_003" and iso_p3.validated_deal.effective_unit_price == Decimal("2400.00")
    assert iso_p3.validated_deal.product_id == "prod_003" and iso_p3.validated_deal.effective_unit_price == Decimal("2425.00")

    iso_p1 = AgentOrchestrator.process_user_message(sid_iso, "prod_001", "Can I get it for 80?")
    assert iso_p1.validated_deal.product_id == "prod_001" and iso_p1.validated_deal.effective_unit_price == Decimal("100.00")
    assert iso_p1.negotiation_round == 0

    iso_p4 = AgentOrchestrator.process_user_message(sid_iso, "prod_004", "Can I get under 1000?")
    assert iso_p4.validated_deal.product_id == "prod_004" and iso_p4.negotiation_round == 1
    print("[PASS] Cross-product isolation verified across prod_003, prod_001, and prod_004.")

    # ----------------------------------------------------
    # TEST 8: Zero Private Seller Values Leaked
    # ----------------------------------------------------
    exp = session_db.export_agent_session(sid_lowball)
    exp_json = exp.model_dump_json()
    for secret in ["reservation_price", "target_price", "aspiration_price", "batna"]:
        assert secret not in exp_json, f"LEAK DETECTED: {secret} in exported session!"
    print("[PASS] Security boundary verified: Zero seller secrets in buyer sessions.")

    print("\n[SUCCESS] ALL SALESPERSON-STYLE NEGOTIATION TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    test_salesperson_economics()

