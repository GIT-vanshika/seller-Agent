import os
import hmac
import hashlib
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.razorpay_service import (
    RazorpayService,
    RazorpayOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerificationResponse,
)
from app.data_loader import db
from app.session_manager import session_db, SessionState
from app.deal_validator import ValidatedDeal


def test_dual_mode_razorpay_suite():
    print("==================================================================")
    print("      RUNNING AURA DUAL-MODE RAZORPAY TEST SUITE")
    print("==================================================================")

    policy = db.get_seller_policy("prod_003")
    assert policy is not None

    # ------------------------------------------------------------------
    # 1. Fallback Simulation Mode (when credentials absent)
    # ------------------------------------------------------------------
    print("\n--- Test 1: Fallback simulation mode when credentials absent ---")
    old_key = os.environ.pop("RAZORPAY_KEY_ID", None)
    old_sec = os.environ.pop("RAZORPAY_KEY_SECRET", None)

    try:
        assert RazorpayService.is_live_test_mode() is False

        req = RazorpayOrderRequest(
            session_id="sess_sim_01",
            product_id="prod_003",
            quantity=5,
            requested_unit_price=Decimal("1763.00"),
            total_payable_amount=Decimal("8815.00"),
        )
        # Authorize 1763 for 5 units
        order_res = RazorpayService.create_order_safe(
            policy=policy,
            request=req,
            current_negotiated_unit_price=Decimal("2150.00"),
            negotiation_round=5,
        )
        assert order_res.is_simulated is True
        assert order_res.key_id is None
        assert order_res.order_id.startswith("order_rzp_")
        assert order_res.amount_in_paisa == 881500
        assert "key_secret" not in order_res.model_dump()
        print(f"[PASS] Simulation order created: {order_res.order_id} ({order_res.amount_in_paisa} paise).")

        # Create session and test verification in simulation mode
        session = session_db.get_or_create_session("sess_sim_01", "prod_003")
        session.last_validated_deal = ValidatedDeal(
            deal_id="deal_test_01",
            product_id="prod_003",
            quantity=5,
            listed_price=Decimal("2500.00"),
            proposed_unit_price=Decimal("1763.00"),
            effective_unit_price=Decimal("1763.00"),
            total_payable_amount=Decimal("8815.00"),
            pricing_mode="negotiable",
            is_valid=True,
            validation_code="AF-TEST",
            validation_message="Valid deal",
            applied_rule_description="18% volume discount",
        )

        payment_id = "pay_sim_123"
        valid_sig = RazorpayService.generate_test_signature(order_res.order_id, payment_id)
        ver_res = RazorpayService.verify_payment_safe(
            session_id="sess_sim_01",
            order_id=order_res.order_id,
            payment_id=payment_id,
            signature=valid_sig,
            session=session,
        )
        assert ver_res.success is True
        assert ver_res.payment_status == "PAYMENT_CAPTURED"
        assert ver_res.escrow_status == "ESCROW_RESERVED"
        assert ver_res.effective_unit_price == Decimal("1763.00")
        assert ver_res.total_payable_amount == Decimal("8815.00")
        assert ver_res.quantity == 5
        print("[PASS] Simulation signature verification & escrow reservation passed.")

    finally:
        if old_key:
            os.environ["RAZORPAY_KEY_ID"] = old_key
        if old_sec:
            os.environ["RAZORPAY_KEY_SECRET"] = old_sec

    # ------------------------------------------------------------------
    # 2. Live Test Mode Order Creation (Mocked API response)
    # ------------------------------------------------------------------
    print("\n--- Test 2: Live Test Mode Order Creation (with credentials) ---")
    test_key_id = "rzp_test_AuraMockKey999"
    test_key_sec = "AuraMockSecretKey888"
    os.environ["RAZORPAY_KEY_ID"] = test_key_id
    os.environ["RAZORPAY_KEY_SECRET"] = test_key_sec

    try:
        assert RazorpayService.is_live_test_mode() is True

        mock_rzp_response = MagicMock()
        mock_rzp_response.status_code = 200
        mock_rzp_response.json.return_value = {
            "id": "order_live_test_mock_456",
            "entity": "order",
            "amount": 881500,
            "amount_paid": 0,
            "amount_due": 881500,
            "currency": "INR",
            "receipt": "rcpt_sess_live_01",
            "status": "created",
            "attempts": 0,
        }

        with patch("requests.post", return_value=mock_rzp_response) as mock_post:
            req_live = RazorpayOrderRequest(
                session_id="sess_live_01",
                product_id="prod_003",
                quantity=5,
                requested_unit_price=Decimal("1763.00"),
                total_payable_amount=Decimal("8815.00"),
            )
            live_order_res = RazorpayService.create_order_safe(
                policy=policy,
                request=req_live,
                current_negotiated_unit_price=Decimal("2150.00"),
                negotiation_round=5,
            )

            # Verify outbound call parameters
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["auth"] == (test_key_id, test_key_sec)
            assert call_kwargs["json"]["amount"] == 881500
            assert call_kwargs["json"]["currency"] == "INR"

            # Verify response
            assert live_order_res.is_simulated is False
            assert live_order_res.order_id == "order_live_test_mock_456"
            assert live_order_res.key_id == test_key_id
            assert "AuraMockSecretKey888" not in live_order_res.model_dump().values()
            print(f"[PASS] Real Test Mode order created: {live_order_res.order_id} with key_id {live_order_res.key_id}.")

            # Test real signature verification with real secret
            session_live = session_db.get_or_create_session("sess_live_01", "prod_003")
            session_live.last_validated_deal = session.last_validated_deal

            live_payment_id = "pay_live_test_789"
            real_msg = f"{live_order_res.order_id}|{live_payment_id}".encode("utf-8")
            real_sig = hmac.new(test_key_sec.encode("utf-8"), real_msg, hashlib.sha256).hexdigest()

            ver_live_res = RazorpayService.verify_payment_safe(
                session_id="sess_live_01",
                order_id=live_order_res.order_id,
                payment_id=live_payment_id,
                signature=real_sig,
                session=session_live,
            )
            assert ver_live_res.success is True
            assert ver_live_res.payment_status == "PAYMENT_CAPTURED"
            assert ver_live_res.order_id == "order_live_test_mock_456"
            print("[PASS] Official HMAC SHA-256 signature verified against test secret.")

    finally:
        os.environ.pop("RAZORPAY_KEY_ID", None)
        os.environ.pop("RAZORPAY_KEY_SECRET", None)

    # ------------------------------------------------------------------
    # 3. Security: Tampering & Invalid Signatures strictly REJECTED
    # ------------------------------------------------------------------
    print("\n--- Test 3: Security & Tampering Defense ---")

    # A: Invalid signature
    try:
        RazorpayService.verify_payment_safe(
            session_id="sess_sim_01",
            order_id=order_res.order_id,
            payment_id="pay_sim_123",
            signature="bad_fake_signature_hex_000000000000000000000000000000000000000000",
            session=session,
        )
        assert False, "Expected ValueError on signature mismatch"
    except ValueError as e:
        assert "signature mismatch" in str(e).lower()
        print("[PASS] Invalid signature strictly REJECTED with ValueError.")

    # B: Price Tampering (Buyer requests ₹100 instead of ₹1763)
    try:
        tamper_req = RazorpayOrderRequest(
            session_id="sess_sim_01",
            product_id="prod_003",
            quantity=5,
            requested_unit_price=Decimal("100.00"),
            total_payable_amount=Decimal("500.00"),
        )
        RazorpayService.create_order_safe(
            policy=policy,
            request=tamper_req,
            current_negotiated_unit_price=Decimal("2150.00"),
            negotiation_round=5,
        )
        assert False, "Expected ValueError on price tampering"
    except ValueError as e:
        assert "tampering" in str(e).lower() or "validation failure" in str(e).lower()
        print("[PASS] Price tampering (Rs.100 vs Rs.1763) strictly REJECTED.")

    # C: Total Amount Tampering (Buyer requests ₹1 total)
    try:
        tamper_tot_req = RazorpayOrderRequest(
            session_id="sess_sim_01",
            product_id="prod_003",
            quantity=5,
            requested_unit_price=Decimal("1763.00"),
            total_payable_amount=Decimal("1.00"),
        )
        RazorpayService.create_order_safe(
            policy=policy,
            request=tamper_tot_req,
            current_negotiated_unit_price=Decimal("2150.00"),
            negotiation_round=5,
        )
        assert False, "Expected ValueError on total tampering"
    except ValueError as e:
        assert "tampering" in str(e).lower()
        print("[PASS] Total amount tampering (Rs.1 vs Rs.8815) strictly REJECTED.")

    # D: Verification without valid deal
    try:
        empty_session = session_db.get_or_create_session("sess_empty", "prod_003")
        RazorpayService.verify_payment_safe(
            session_id="sess_empty",
            order_id="order_123",
            payment_id="pay_123",
            signature="sig_123",
            session=empty_session,
        )
        assert False, "Expected ValueError on missing deal"
    except ValueError as e:
        assert "no validated deal found" in str(e).lower()
        print("[PASS] Verification without validated deal strictly REJECTED.")

    print("\n==================================================================")
    print("   [SUCCESS] ALL DUAL-MODE RAZORPAY TESTS PASSED 100%!")
    print("==================================================================\n")


if __name__ == "__main__":
    test_dual_mode_razorpay_suite()
