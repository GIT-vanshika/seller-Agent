from decimal import Decimal
from app.models import SellerPolicy, Product
from app.data_loader import db
from app.policy_engine import PolicyEngine
from app.deal_validator import DealConsistencyValidator, DealValidationRequest
from app.session_manager import session_db
from app.orchestrator import AgentOrchestrator


def run_economic_boundary_tests():
    print("==================================================================")
    print("   RUNNING QUESTION 3 ECONOMIC BOUNDARY & PRICING PATH TEST SUITE  ")
    print("==================================================================")

    prod_003 = db.get_product("prod_003")
    policy_003 = db.get_seller_policy("prod_003")

    prod_004 = db.get_product("prod_004")
    policy_004 = db.get_seller_policy("prod_004")

    # ------------------------------------------------------------------
    # Case 1: Single-unit negotiation (prod_003, qty=1)
    # ------------------------------------------------------------------
    req_1 = DealValidationRequest(
        product_id="prod_003",
        quantity=1,
        proposed_unit_price=Decimal("2092.00"),
        seller_authorized_price=Decimal("2092.00"),
        negotiation_round=1,
    )
    val_1 = DealConsistencyValidator.validate_deal(policy_003, req_1)
    assert val_1.is_valid
    assert val_1.effective_unit_price == Decimal("2092.00")
    assert val_1.total_payable_amount == Decimal("2092.00")
    print("[PASS] Case 1: Single-unit negotiation validated at exact authorized price Rs.2092.00.")

    # ------------------------------------------------------------------
    # Case 2: Quantity exactly at bulk threshold (prod_004, qty=5)
    # ------------------------------------------------------------------
    # Qty 5 triggers tier 10% discount: Rs.1200 * 0.9 = Rs.1080.00
    req_2 = DealValidationRequest(
        product_id="prod_004",
        quantity=5,
        proposed_unit_price=Decimal("1080.00"),
        seller_authorized_price=Decimal("1080.00"),
        negotiation_round=1,
    )
    val_2 = DealConsistencyValidator.validate_deal(policy_004, req_2)
    assert val_2.is_valid
    assert val_2.effective_unit_price == Decimal("1080.00")
    assert val_2.total_payable_amount == Decimal("5400.00")
    print("[PASS] Case 2: Quantity exactly at bulk threshold (qty=5) validated at Rs.1080.00 (Total: Rs.5400.00).")

    # ------------------------------------------------------------------
    # Case 3: Quantity above bulk threshold (prod_004, qty=12)
    # ------------------------------------------------------------------
    # Qty 12 triggers tier 18% discount: Rs.1200 * 0.82 = Rs.984.00
    req_3 = DealValidationRequest(
        product_id="prod_004",
        quantity=12,
        proposed_unit_price=Decimal("984.00"),
        seller_authorized_price=Decimal("984.00"),
        negotiation_round=1,
    )
    val_3 = DealConsistencyValidator.validate_deal(policy_004, req_3)
    assert val_3.is_valid
    assert val_3.effective_unit_price == Decimal("984.00")
    assert val_3.total_payable_amount == Decimal("11808.00")
    print("[PASS] Case 3: Quantity above bulk threshold (qty=12) validated at Rs.984.00 (Total: Rs.11808.00).")

    # ------------------------------------------------------------------
    # Case 4: Negotiated price above bulk baseline
    # ------------------------------------------------------------------
    req_4 = DealValidationRequest(
        product_id="prod_004",
        quantity=5,
        proposed_unit_price=Decimal("1100.00"),
        seller_authorized_price=Decimal("1080.00"),
        negotiation_round=1,
    )
    val_4 = DealConsistencyValidator.validate_deal(policy_004, req_4)
    assert val_4.is_valid
    assert val_4.effective_unit_price == Decimal("1080.00")  # Best authorized bulk price applied
    print("[PASS] Case 4: Proposed price above bulk baseline capped at best authorized bulk price.")

    # ------------------------------------------------------------------
    # Case 5: Negotiated price equal to bulk baseline
    # ------------------------------------------------------------------
    req_5 = DealValidationRequest(
        product_id="prod_004",
        quantity=5,
        proposed_unit_price=Decimal("1080.00"),
        seller_authorized_price=Decimal("1080.00"),
        negotiation_round=1,
    )
    val_5 = DealConsistencyValidator.validate_deal(policy_004, req_5)
    assert val_5.is_valid
    assert val_5.effective_unit_price == Decimal("1080.00")
    print("[PASS] Case 5: Negotiated price equal to bulk baseline validated cleanly.")

    # ------------------------------------------------------------------
    # Case 6: Negotiated price below bulk baseline but above reservation
    # ------------------------------------------------------------------
    # Suppose PolicyEngine authorized Rs.850 from anchor Rs.944.44 (10% bulk tier: 944.44 * 0.90 = 850)
    req_6 = DealValidationRequest(
        product_id="prod_004",
        quantity=5,
        proposed_unit_price=Decimal("850.00"),
        seller_authorized_price=Decimal("850.00"),
        current_negotiated_unit_price=Decimal("944.44"),
        negotiation_round=4,
    )
    val_6 = DealConsistencyValidator.validate_deal(policy_004, req_6)
    assert val_6.is_valid
    assert val_6.effective_unit_price == Decimal("850.00")
    assert val_6.effective_unit_price >= policy_004.reservation_price
    print("[PASS] Case 6: Negotiated price below bulk baseline validated when explicitly authorized by PolicyEngine.")

    # ------------------------------------------------------------------
    # Case 7: Attempt to inject a fake seller_authorized_price
    # ------------------------------------------------------------------
    req_7 = DealValidationRequest(
        product_id="prod_003",
        quantity=1,
        proposed_unit_price=Decimal("500.00"),
        seller_authorized_price=Decimal("500.00"),  # Fake tampered seller price below floor
        negotiation_round=1,
    )
    val_7 = DealConsistencyValidator.validate_deal(policy_003, req_7)
    assert not val_7.is_valid
    assert val_7.validation_code in ["EXCEEDS_RESERVATION_FLOOR", "OFFER_BELOW_SELLER_THRESHOLD"]
    print("[PASS] Case 7: Attempt to inject fake seller_authorized_price strictly REJECTED.")

    # ------------------------------------------------------------------
    # Case 8: Attempt to submit multiple candidate prices & force cheapest
    # ------------------------------------------------------------------
    req_8 = DealValidationRequest(
        product_id="prod_003",
        quantity=1,
        proposed_unit_price=Decimal("1200.00"),
        seller_authorized_price=Decimal("2092.00"),  # Official authorized price
        current_negotiated_unit_price=Decimal("1550.00"),  # Client attempts to force reservation floor
        negotiation_round=1,
    )
    val_8 = DealConsistencyValidator.validate_deal(policy_003, req_8)
    assert not val_8.is_valid
    assert val_8.validation_code in ["EXCEEDS_RESERVATION_FLOOR", "OFFER_BELOW_SELLER_THRESHOLD"]
    assert val_8.effective_unit_price == Decimal("2092.00")
    print("[PASS] Case 8: Attempt to force lower candidate price REJECTED; authorized threshold enforced.")

    # ------------------------------------------------------------------
    # Case 9: Attempt to change quantity after negotiation
    # ------------------------------------------------------------------
    # Negotiating single unit at target, then requesting 100 units
    target_p3 = policy_003.target_price
    dec_9 = PolicyEngine.evaluate_offer(policy_003, buyer_offer=target_p3, round_number=1, quantity=100)
    req_9 = DealValidationRequest(
        product_id="prod_003",
        quantity=100,
        proposed_unit_price=target_p3,
        seller_authorized_price=dec_9.seller_authorized_price,
        negotiation_round=1,
    )
    val_9 = DealConsistencyValidator.validate_deal(policy_003, req_9)
    assert val_9.is_valid
    assert val_9.quantity == 100
    assert val_9.total_payable_amount == target_p3 * 100
    print(f"[PASS] Case 9: Quantity change re-evaluated and validated for exact quantity (Rs.{val_9.total_payable_amount:.2f}).")

    # ------------------------------------------------------------------
    # Case 10: Attempt to reuse single-unit negotiated deal for bulk quantity
    # ------------------------------------------------------------------
    # Single-unit deal agreed at Rs.2092. Client attempts to buy 10 units at Rs.2092 without bulk re-evaluation
    dec_10 = PolicyEngine.evaluate_offer(policy_004, buyer_offer=Decimal("1000.00"), round_number=1, quantity=10)
    req_10 = DealValidationRequest(
        product_id="prod_004",
        quantity=10,
        proposed_unit_price=Decimal("1000.00"),
        seller_authorized_price=dec_10.seller_authorized_price,
        negotiation_round=1,
    )
    val_10 = DealConsistencyValidator.validate_deal(policy_004, req_10)
    assert val_10.effective_unit_price == Decimal("984.00")  # Bulk tier for qty 10 gives Rs.984.00!
    print("[PASS] Case 10: Bulk order automatically receives best authorized bulk tier price (Rs.984.00).")

    # ------------------------------------------------------------------
    # Case 11: Attempt to reuse bulk negotiated deal for single unit
    # ------------------------------------------------------------------
    # Qty 10 bulk price was Rs.984. Client changes quantity to 1 unit at Rs.984
    req_11 = DealValidationRequest(
        product_id="prod_004",
        quantity=1,
        proposed_unit_price=Decimal("984.00"),
        seller_authorized_price=Decimal("1100.00"),  # Round 1 authorized price for single unit is Rs.1100
        negotiation_round=1,
    )
    val_11 = DealConsistencyValidator.validate_deal(policy_004, req_11)
    assert not val_11.is_valid
    assert val_11.validation_code == "OFFER_BELOW_SELLER_THRESHOLD"
    assert val_11.effective_unit_price == Decimal("1100.00")
    print("[PASS] Case 11: Single unit attempting to reuse bulk discount REJECTED.")

    # ------------------------------------------------------------------
    # Case 12: Attempt to alter product_id while retaining old negotiated state
    # ------------------------------------------------------------------
    s_iso = session_db.get_or_create_session("sess_cross_product", "prod_003")
    session_db.record_negotiation_step("sess_cross_product", agreed_price=Decimal("1750.00"), quantity=1)

    # Change product_id to prod_004 in same session
    s_reset = session_db.get_or_create_session("sess_cross_product", "prod_004")
    assert s_reset.product_id == "prod_004"
    assert s_reset.current_negotiated_unit_price is None
    assert s_reset.negotiation_round == 0
    print("[PASS] Case 12: Product ID change cleanly clears session state, preventing cross-product price reuse.")

    print("\n==================================================================")
    print("   [SUCCESS] ALL 12 ECONOMIC BOUNDARY TESTS PASSED 100%!")
    print("==================================================================\n")


if __name__ == "__main__":
    run_economic_boundary_tests()
