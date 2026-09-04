from decimal import Decimal
from app.data_loader import db
from app.policy_engine import PolicyEngine
from app.intent_classifier import IntentClassifier
from app.orchestrator import AgentOrchestrator
from app.session_manager import session_db
from app.razorpay_service import RazorpayService, RazorpayOrderRequest


def test_targeted_corrections():
    print("==================================================")
    print("     TESTING TARGETED CORRECTIONS & VOLUME MODEL  ")
    print("==================================================")

    # ----------------------------------------------------
    # 1. BUG FIX #1: CONDITIONAL BUY INTENT
    # ----------------------------------------------------
    print("\n--- TEST 1: Conditional Buy Intent ---")
    phrases = [
        ("I want to buy this but it's too costly, can I get it under 500", Decimal("500")),
        ("I'd buy it if you can do 700", Decimal("700")),
        ("I want to buy but can you make it cheaper?", None),
        ("I'd like to purchase but could you do 600?", Decimal("600")),
    ]
    for text, exp_price in phrases:
        res = IntentClassifier.classify(text)
        assert res.intent != "checkout_intent", f"Expected negotiation intent for '{text}', got checkout_intent"
        assert res.intent in ["price_hesitation", "price_negotiation"], f"Unexpected intent: {res.intent}"
        if exp_price is not None:
            assert res.offered_price == exp_price, f"Expected {exp_price}, got {res.offered_price}"

    # Orchestrator end-to-end test with conditional buy intent
    sid_cond = "sess_test_conditional_buy"
    chat_res = AgentOrchestrator.process_user_message(
        sid_cond, "prod_004", "I want to buy this but it's too costly, can I get it under 500"
    )
    assert chat_res.can_show_payment is False, "can_show_payment must be False for conditional offer!"
    assert chat_res.intent in ["price_negotiation", "price_hesitation"]
    print("[PASS] Conditional buy intent correctly routed to negotiation, NOT checkout.")

    # ----------------------------------------------------
    # 2. BUG FIX #2: NUMBER / QUANTITY PARSING
    # ----------------------------------------------------
    print("\n--- TEST 2: Quantity Parsing & Price Distinction ---")
    sid_q = "sess_test_quantity_distinction"
    # Round 1 offer
    AgentOrchestrator.process_user_message(sid_q, "prod_004", "Can you do 900?")
    
    # 'But you said ok for 900'
    res_said = AgentOrchestrator.process_user_message(sid_q, "prod_004", "But you said ok for 900")
    assert res_said.quantity == 1, f"Quantity must be 1, got {res_said.quantity}!"
    assert res_said.validated_deal.total_payable_amount < Decimal("10000.00"), f"Total payable exploded to {res_said.validated_deal.total_payable_amount}"
    print(f"[PASS] 'But you said ok for 900' preserved quantity=1 (Total: Rs.{res_said.validated_deal.total_payable_amount:.2f}).")

    # ----------------------------------------------------
    # 3. COMMERCIAL MODEL: MULTI-UNIT / VOLUME DEAL TRANSITION
    # ----------------------------------------------------
    print("\n--- TEST 3: Multi-Unit / Volume Commercial Model ---")
    policy_004 = db.get_seller_policy("prod_004")
    assert policy_004 is not None

    # Step 3A: Single unit negotiation on prod_004 down to final firm price of 900
    sid_vol = "sess_test_volume_transition"
    for r in range(1, 8):
        step_res = AgentOrchestrator.process_user_message(sid_vol, "prod_004", "800 final")
    
    assert step_res.negotiation_round == 7
    assert step_res.current_negotiated_unit_price == Decimal("900.00")
    assert step_res.can_show_payment is False, "Round 7 reaches policy boundary, NEGOTIATION FINISHED != BUYER ACCEPTED"

    # Step 3B: Buyer asks: 'What if I buy 2 units?'
    # Rules:
    # - DO NOT multiply 1-unit negotiated price (900 * 2 != 1800)
    # - DO NOT restart 1-unit concession curve
    # - Bulk tiers for prod_004 start at 5 units (10% off)
    # - For 2 units, no volume discount qualifies -> catalog price Rs.1200 applies -> Total Rs.2400
    res_2units = AgentOrchestrator.process_user_message(sid_vol, "prod_004", "What if I buy 2 units?")
    assert res_2units.quantity == 2, f"Expected quantity 2, got {res_2units.quantity}"
    assert res_2units.validated_deal.effective_unit_price == Decimal("1200.00"), f"Expected 1200, got {res_2units.validated_deal.effective_unit_price}"
    assert res_2units.validated_deal.total_payable_amount == Decimal("2400.00"), f"Expected 2400, got {res_2units.validated_deal.total_payable_amount}"
    assert "volume" in res_2units.message.lower()
    assert "begin at 5 units" in res_2units.message or "5 units" in res_2units.message
    print(f"[PASS] 2 units transition: Rs.1200/unit, Total Rs.2400 (Did NOT multiply Rs.900 × 2). Explanation provided.")

    # Step 3C: Buyer asks for 5 units (Qualifies for 10% volume tier)
    # Formula:
    # base_total = 1200 * 5 = 6000
    # volume_discount = 10% (-600)
    # final_total = 5400
    # effective_unit_price = 1080
    res_5units = AgentOrchestrator.process_user_message(sid_vol, "prod_004", "What about 5 units?")
    assert res_5units.quantity == 5, f"Expected quantity 5, got {res_5units.quantity}"
    assert res_5units.validated_deal.effective_unit_price == Decimal("1080.00"), f"Expected 1080, got {res_5units.validated_deal.effective_unit_price}"
    assert res_5units.validated_deal.total_payable_amount == Decimal("5400.00"), f"Expected 5400, got {res_5units.validated_deal.total_payable_amount}"
    assert "6,000.00" in res_5units.message or "6000.00" in res_5units.message
    assert "10%" in res_5units.message
    assert "5,400.00" in res_5units.message or "5400.00" in res_5units.message
    assert "1,080.00" in res_5units.message or "1080.00" in res_5units.message
    print("[PASS] 5 units volume tier verified: Base Rs.6000 - 10% (Rs.600) = Rs.5400 (Rs.1080/unit).")

    # Step 3D: Buyer accepts 5 units volume deal: 'Ok done'
    res_accept_vol = AgentOrchestrator.process_user_message(sid_vol, "prod_004", "Ok done")
    assert res_accept_vol.can_show_payment is True
    assert res_accept_vol.validated_deal.quantity == 5
    assert res_accept_vol.validated_deal.total_payable_amount == Decimal("5400.00")
    print("[PASS] Buyer accepted volume deal -> can_show_payment=True, Total Rs.5400.")

    # Step 3E: Order creation for 5 units volume deal
    rzp_req = RazorpayOrderRequest(
        session_id=sid_vol,
        product_id="prod_004",
        quantity=5,
        requested_unit_price=Decimal("1080.00"),
        total_payable_amount=Decimal("5400.00"),
    )
    rzp_order = RazorpayService.create_order_safe(
        policy=policy_004,
        request=rzp_req,
        current_negotiated_unit_price=Decimal("1080.00"),
        negotiation_round=7,
    )
    assert rzp_order.status == "created"
    assert rzp_order.total_payable_amount == Decimal("5400.00")
    assert rzp_order.quantity == 5
    print(f"[PASS] Razorpay order created for volume deal: Order {rzp_order.order_id}, Status: {rzp_order.status}, Total: Rs.{rzp_order.total_payable_amount:.2f}.")

    # ----------------------------------------------------
    # 4. BUG FIX #5: NO DUPLICATE RESPONSE RENDERING
    # ----------------------------------------------------
    print("\n--- TEST 4: No Duplicate Response Text ---")
    sid_dup = "sess_test_duplicate_free"
    # Fresh buy
    r_fresh = AgentOrchestrator.process_user_message(sid_dup, "prod_001", "I want to buy")
    assert r_fresh.message.count("Click 'Pay with Razorpay'") <= 1
    assert r_fresh.message.count("confirmed and locked") <= 1
    assert r_fresh.message.count("Unit Price:") <= 1

    # Negotiated buy
    sid_dup2 = "sess_test_duplicate_free_neg"
    AgentOrchestrator.process_user_message(sid_dup2, "prod_003", "Can I get 2425?")
    r_neg = AgentOrchestrator.process_user_message(sid_dup2, "prod_003", "Ok done")
    assert r_neg.message.count("Click 'Pay with Razorpay'") <= 1
    assert r_neg.message.count("Effective Unit Price:") <= 1
    print("[PASS] Response messages are clean and contain zero duplicate blocks.")

    print("\n[SUCCESS] ALL TARGETED CORRECTION & VOLUME MODEL TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    test_targeted_corrections()
