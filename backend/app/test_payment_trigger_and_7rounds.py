from decimal import Decimal
from app.orchestrator import AgentOrchestrator
from app.session_manager import session_db
from app.razorpay_service import RazorpayService, RazorpayOrderRequest
from app.data_loader import db


def test_payment_triggers_and_7rounds():
    print("================================================================")
    print("   TESTING MULTI-STAGE PAYMENT CONTRACT & 7-ROUND POLICY        ")
    print("================================================================")

    pid = "prod_003"
    policy_003 = db.get_seller_policy(pid)
    assert policy_003 is not None
    assert policy_003.max_negotiation_rounds == 7
    assert policy_003.target_price == Decimal("2050.00")
    assert policy_003.reservation_price == Decimal("1550.00")

    # ------------------------------------------------------------------
    # TEST 1: Case 1 - Explicit Purchase Confidence Triggers Payment
    # ------------------------------------------------------------------
    print("\n--- TEST 1: Case 1 - Explicit Purchase Confidence ---")
    
    # 1A: After active negotiation
    sid_1a = "sess_test_case1a"
    AgentOrchestrator.process_user_message(sid_1a, pid, "Can I get under 1900?")
    r_acc1 = AgentOrchestrator.process_user_message(sid_1a, pid, "Ok done")
    assert r_acc1.can_show_payment is True
    assert r_acc1.deal_status == "agreed"
    assert r_acc1.validated_deal is not None and r_acc1.validated_deal.is_valid is True
    assert r_acc1.validated_deal.effective_unit_price == Decimal("2425.00")
    print("[PASS] 1A: 'Ok done' after negotiation -> can_show_payment=True, deal_status=agreed, price=Rs.2425.00")

    sid_1b = "sess_test_case1b"
    AgentOrchestrator.process_user_message(sid_1b, pid, "Can I get under 1900?")
    r_acc2 = AgentOrchestrator.process_user_message(sid_1b, pid, "I want to buy")
    assert r_acc2.can_show_payment is True
    assert r_acc2.deal_status == "agreed"
    assert r_acc2.validated_deal.is_valid is True
    assert r_acc2.validated_deal.effective_unit_price == Decimal("2425.00")
    print("[PASS] 1B: 'I want to buy' after negotiation -> can_show_payment=True, deal_status=agreed")

    # 1C: Fresh session explicit buy (must use authoritative catalog listed price, zero fabricated discounts)
    sid_1c = "sess_test_case1c"
    r_acc3 = AgentOrchestrator.process_user_message(sid_1c, pid, "I want to buy")
    assert r_acc3.can_show_payment is True
    assert r_acc3.deal_status == "agreed"
    assert r_acc3.validated_deal.is_valid is True
    assert r_acc3.validated_deal.effective_unit_price == Decimal("2500.00")
    print("[PASS] 1C: 'I want to buy' on fresh session -> authoritative catalog price Rs.2500.00, can_show_payment=True")

    # ------------------------------------------------------------------
    # TEST 2: Case 2 - Explicit Payment Inquiry Triggers Payment
    # ------------------------------------------------------------------
    print("\n--- TEST 2: Case 2 - Explicit Payment Inquiry ---")

    # 2A: "where can I pay?" after negotiation
    sid_2a = "sess_test_case2a"
    AgentOrchestrator.process_user_message(sid_2a, pid, "Can I get under 1900?")
    r_inq1 = AgentOrchestrator.process_user_message(sid_2a, pid, "where can I pay?")
    assert r_inq1.can_show_payment is True
    assert r_inq1.deal_status == "agreed"
    assert r_inq1.validated_deal.is_valid is True
    assert r_inq1.validated_deal.effective_unit_price == Decimal("2425.00")
    assert "Razorpay" in r_inq1.message or "pay" in r_inq1.message.lower()
    print("[PASS] 2A: 'where can I pay?' after negotiation -> can_show_payment=True, deal_status=agreed")

    # 2B: "where to to pay for it" (matching prompt phrasing)
    sid_2b = "sess_test_case2b"
    AgentOrchestrator.process_user_message(sid_2b, pid, "Can I get under 1900?")
    r_inq2 = AgentOrchestrator.process_user_message(sid_2b, pid, "where to to pay for it")
    assert r_inq2.can_show_payment is True
    assert r_inq2.deal_status == "agreed"
    assert r_inq2.validated_deal.is_valid is True
    print("[PASS] 2B: 'where to to pay for it' -> can_show_payment=True, deal_status=agreed")

    # 2C: "how can I pay?" on fresh session -> authoritative catalog price
    sid_2c = "sess_test_case2c"
    r_inq3 = AgentOrchestrator.process_user_message(sid_2c, pid, "how can I pay?")
    assert r_inq3.can_show_payment is True
    assert r_inq3.deal_status == "agreed"
    assert r_inq3.validated_deal.is_valid is True
    assert r_inq3.validated_deal.effective_unit_price == Decimal("2500.00")
    print("[PASS] 2C: 'how can I pay?' on fresh session -> authoritative catalog price Rs.2500.00, can_show_payment=True")

    # ------------------------------------------------------------------
    # TEST 3: Case 3 - 7 Rounds & NEGOTIATION FINISHED != BUYER ACCEPTED
    # ------------------------------------------------------------------
    print("\n--- TEST 3: 7 Rounds & NEGOTIATION FINISHED != BUYER ACCEPTED ---")
    sid_7r = "sess_test_7rounds_lifecycle"

    # Rounds 1 to 6: Lowball offers, can_show_payment MUST be False, deal_status MUST be negotiating
    concession_steps = [
        (1, "Can I get it for 1800?", Decimal("2425.00")),
        (2, "Ok 1800 then", Decimal("2350.00")),
        (3, "How about 1850?", Decimal("2275.00")),
        (4, "Can you do 1900?", Decimal("2200.00")),
        (5, "What about 1950?", Decimal("2150.00")),
        (6, "Give it for 2000", Decimal("2100.00")),
    ]
    for r_num, text, exp_counter in concession_steps:
        res = AgentOrchestrator.process_user_message(sid_7r, pid, text)
        assert res.negotiation_round == r_num
        assert res.can_show_payment is False, f"Premature payment exposure in round {r_num}!"
        assert res.deal_status == "negotiating"
        assert res.validated_deal.effective_unit_price == exp_counter
        print(f"  [OK] Round {r_num}: Counter Rs.{exp_counter}, can_show_payment=False, deal_status=negotiating")

    # Round 7: FINAL POLICY BOUNDARY REACHED
    print("\n  Executing Round 7 (Final Policy Boundary)...")
    res_r7 = AgentOrchestrator.process_user_message(sid_7r, pid, "Can you do 1900 final?")
    assert res_r7.negotiation_round == 7
    
    # 1. Final authoritative seller price established at target (Rs.2050.00)
    assert res_r7.validated_deal.effective_unit_price == Decimal("2050.00")
    s_r7 = session_db.get_session(sid_7r)
    assert s_r7.current_negotiated_unit_price == Decimal("2050.00")

    # 2. Tell the buyer: "We cannot get below ₹X. It is against seller policy."
    assert "cannot get below" in res_r7.message.lower()
    assert "against seller policy" in res_r7.message.lower()
    assert "2050" in res_r7.message

    # 3. NO "limit" or "maximum negotiation rounds" language
    msg_lower = res_r7.message.lower()
    assert "maximum negotiation rounds" not in msg_lower, f"Forbidden limit language in: {res_r7.message}"
    assert "reached limit" not in msg_lower, f"Forbidden limit language in: {res_r7.message}"
    assert "reached the limit" not in msg_lower, f"Forbidden limit language in: {res_r7.message}"
    assert "exceeded" not in msg_lower, f"Forbidden limit language in: {res_r7.message}"

    # 4. NEGOTIATION FINISHED != BUYER ACCEPTED:
    # Do not mark deal as agreed, do not expose payment prematurely
    assert res_r7.deal_status == "negotiating", f"Expected negotiating, got {res_r7.deal_status}"
    assert res_r7.can_show_payment is False, "Payment should NOT appear before buyer acceptance!"
    print("[PASS] Round 7: Final firm price Rs.2050.00 established. Zero limit language. deal_status=negotiating, can_show_payment=False.")

    # 5. BUYER ACCEPTS: Now buyer sends "Ok done"
    print("\n  Buyer sends 'Ok done' to accept established final firm price...")
    res_agree = AgentOrchestrator.process_user_message(sid_7r, pid, "Ok done")
    assert res_agree.deal_status == "agreed"
    assert res_agree.can_show_payment is True
    assert res_agree.validated_deal.is_valid is True
    assert res_agree.validated_deal.effective_unit_price == Decimal("2050.00")
    print("[PASS] BUYER_ACCEPTS -> DEAL_AGREED -> can_show_payment=True, price=Rs.2050.00")

    # 6. RAZORPAY ORDER: Create order at validated Rs.2050.00
    rzp_req = RazorpayOrderRequest(
        session_id=sid_7r,
        product_id=pid,
        quantity=1,
        requested_unit_price=Decimal("2050.00"),
        total_payable_amount=Decimal("2050.00"),
    )
    rzp_order = RazorpayService.create_order_safe(
        policy=policy_003,
        request=rzp_req,
        current_negotiated_unit_price=Decimal("2050.00"),
        negotiation_round=7,
    )
    assert rzp_order.status == "created"
    assert rzp_order.total_payable_amount == Decimal("2050.00")
    assert rzp_order.order_id.startswith("order_rzp_")
    print(f"[PASS] RAZORPAY order created: {rzp_order.order_id} for Rs.{rzp_order.total_payable_amount}")

    # ------------------------------------------------------------------
    # TEST 4: Hard Floor Boundary Security
    # ------------------------------------------------------------------
    print("\n--- TEST 4: Hard Floor Boundary Security ---")
    try:
        tampered_req = RazorpayOrderRequest(
            session_id=sid_7r,
            product_id=pid,
            quantity=1,
            requested_unit_price=Decimal("1200.00"),  # Below reservation price 1550
            total_payable_amount=Decimal("1200.00"),
        )
        RazorpayService.create_order_safe(
            policy=policy_003,
            request=tampered_req,
            current_negotiated_unit_price=Decimal("1200.00"),
            negotiation_round=7,
        )
        assert False, "Tampered price below reservation price should have failed!"
    except ValueError as e:
        print(f"[PASS] Sub-floor tampering rejected: {e}")

    print("\n================================================================")
    print("   [SUCCESS] ALL MULTI-STAGE PAYMENT CONTRACT TESTS PASSED 100%!  ")
    print("================================================================")


if __name__ == "__main__":
    test_payment_triggers_and_7rounds()

