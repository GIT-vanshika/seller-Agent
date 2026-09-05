import uuid
import hmac
import hashlib
import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from pydantic import BaseModel
from app.deal_validator import DealConsistencyValidator, ValidatedDeal, DealValidationRequest
from app.policy_engine import PolicyEngine, PolicyEngineDecision
from app.models import SellerPolicy

_env_path = Path(__file__).resolve().parent.parent / ".env"

def reload_env():
    if _env_path.exists():
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
                        if _k and _v:
                            os.environ[_k] = _v
        except Exception:
            pass

reload_env()

logger = logging.getLogger("razorpay_service")

if TYPE_CHECKING:
    from app.session_manager import SessionState


class RazorpayOrderRequest(BaseModel):
    session_id: str
    product_id: str
    quantity: int
    requested_unit_price: Decimal
    total_payable_amount: Decimal


class RazorpayOrderResponse(BaseModel):
    order_id: str
    status: str  # "created"
    amount_in_paisa: int
    currency: str  # "INR"
    receipt: str
    product_id: str
    quantity: int
    effective_unit_price: Decimal
    total_payable_amount: Decimal
    key_id: Optional[str] = None
    is_simulated: bool = False
    message: str


class RazorpayVerificationResponse(BaseModel):
    success: bool
    payment_status: str  # "PAYMENT_CAPTURED"
    escrow_status: str   # "ESCROW_RESERVED"
    order_id: str
    payment_id: str
    session_id: str
    amount_in_paisa: int
    currency: str
    effective_unit_price: Decimal
    total_payable_amount: Decimal
    quantity: Optional[int] = 1
    message: str


class RazorpayService:
    """
    Pre-Checkout Razorpay Order Creation Service.
    Pre-Checkout Razorpay Order Creation & Post-Payment Cryptographic Verification Service.
    Determines final payable amount ONLY by executing PolicyEngine & DealConsistencyValidator on the backend control plane.
    Rejects any unvalidated, tampered, or invalid deal requests.
    Enforces strict payment lifecycle: VALIDATED_DEAL -> ORDER_CREATED -> RAZORPAY_CHECKOUT -> SERVER-SIDE HMAC VERIFICATION -> PAYMENT_CAPTURED -> ESCROW_RESERVED.
    """

    DEFAULT_KEY_SECRET = "mock_secret_key_aura_mvp_2026"

    @classmethod
    def get_key_id(cls) -> Optional[str]:
        return os.environ.get("RAZORPAY_KEY_ID")

    @classmethod
    def get_server_secret(cls) -> str:
        return os.environ.get("RAZORPAY_KEY_SECRET") or cls.DEFAULT_KEY_SECRET

    @classmethod
    def is_live_test_mode(cls) -> bool:
        key_id = cls.get_key_id()
        key_sec = os.environ.get("RAZORPAY_KEY_SECRET")
        return bool(key_id and key_sec and key_id.startswith("rzp_test_"))

    @classmethod
    def generate_test_signature(cls, order_id: str, payment_id: str, secret: Optional[str] = None) -> str:
        key_secret = secret or cls.get_server_secret()
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        return hmac.new(key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    @classmethod
    def verify_payment_signature(
        cls,
        order_id: str,
        payment_id: str,
        signature: str,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Standard Razorpay server-side HMAC SHA-256 signature verification.
        Message format: f"{order_id}|{payment_id}"
        Key: server-side RAZORPAY_KEY_SECRET (never exposed to client).
        """
        expected_sig = cls.generate_test_signature(order_id, payment_id, secret=secret)
        return hmac.compare_digest(expected_sig, signature)

    @classmethod
    def create_order_safe(
        cls,
        policy: SellerPolicy,
        request: RazorpayOrderRequest,
        current_negotiated_unit_price: Optional[Decimal] = None,
        negotiation_round: int = 1,
    ) -> RazorpayOrderResponse:
        # Step 1: Re-evaluate PolicyEngine to obtain seller-authorized price
        decision: PolicyEngineDecision = PolicyEngine.evaluate_offer(
            policy=policy,
            buyer_offer=request.requested_unit_price,
            round_number=negotiation_round,
            quantity=request.quantity,
            negotiated_unit_price=current_negotiated_unit_price,
        )

        # Step 2: Re-run DealConsistencyValidator deterministically on server policy
        validation_req = DealValidationRequest(
            product_id=request.product_id,
            quantity=request.quantity,
            proposed_unit_price=request.requested_unit_price,
            seller_authorized_price=decision.seller_authorized_price,
            current_negotiated_unit_price=current_negotiated_unit_price,
            negotiation_round=negotiation_round,
            buyer_committed=True,
        )

        validated_deal: ValidatedDeal = DealConsistencyValidator.validate_deal(policy, validation_req)

        # Check if buyer is checking out at a previously agreed session price
        is_session_agreed_price = (
            current_negotiated_unit_price is not None
            and request.requested_unit_price == current_negotiated_unit_price
            and request.requested_unit_price >= policy.reservation_price
        )

        # Check 1: Deal MUST be authorized by PolicyEngine OR agreed in active session AND valid by DealConsistencyValidator
        if not (decision.accepted or is_session_agreed_price) or not validated_deal.is_valid:
            raise ValueError(f"PRE-CHECKOUT VALIDATION FAILURE: {validated_deal.validation_message}")

        # Check 2: Requested price/total MUST match backend DealConsistencyValidator's effective price & total
        if validated_deal.effective_unit_price != request.requested_unit_price:
            raise ValueError(
                f"PRICE TAMPERING DETECTED: Requested unit price (₹{request.requested_unit_price:.2f}) "
                f"differs from backend validated price (₹{validated_deal.effective_unit_price:.2f})"
            )

        if validated_deal.total_payable_amount != request.total_payable_amount:
            raise ValueError(
                f"PRICE TAMPERING DETECTED: Requested total (₹{request.total_payable_amount:.2f}) "
                f"differs from backend validated total (₹{validated_deal.total_payable_amount:.2f})"
            )

        # Generate Razorpay Order
        total_paisa = int(validated_deal.total_payable_amount * Decimal("100"))
        receipt_id = f"rcpt_{request.session_id[:16]}_{uuid.uuid4().hex[:6]}"

        # Dual-Mode: Call official Razorpay Orders API if test credentials configured
        if cls.is_live_test_mode():
            key_id = cls.get_key_id()
            key_secret = cls.get_server_secret()
            try:
                import requests
                api_url = "https://api.razorpay.com/v1/orders"
                payload = {
                    "amount": total_paisa,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "notes": {
                        "session_id": request.session_id,
                        "product_id": request.product_id,
                        "quantity": str(validated_deal.quantity),
                        "unit_price": str(validated_deal.effective_unit_price),
                        "platform": "AURA_Agent",
                    },
                }
                res = requests.post(api_url, auth=(key_id, key_secret), json=payload, timeout=10)
                if res.status_code in [200, 201]:
                    rzp_order = res.json()
                    order_id = rzp_order["id"]
                    logger.info(f"Created real Razorpay Test Mode order: {order_id} for {total_paisa} paise")
                    return RazorpayOrderResponse(
                        order_id=order_id,
                        status="created",
                        amount_in_paisa=total_paisa,
                        currency="INR",
                        receipt=receipt_id,
                        product_id=request.product_id,
                        quantity=validated_deal.quantity,
                        effective_unit_price=validated_deal.effective_unit_price,
                        total_payable_amount=validated_deal.total_payable_amount,
                        key_id=key_id,
                        is_simulated=False,
                        message="Official Razorpay Test Mode Order created successfully.",
                    )
                else:
                    logger.error(f"Razorpay API order creation failed ({res.status_code}): {res.text}. Falling back to simulation.")
            except Exception as e:
                logger.error(f"Razorpay API connection error: {str(e)}. Falling back to simulation.")

        # Simulation fallback (when credentials are not configured or offline)
        order_id = f"order_rzp_{uuid.uuid4().hex[:12]}"
        return RazorpayOrderResponse(
            order_id=order_id,
            status="created",
            amount_in_paisa=total_paisa,
            currency="INR",
            receipt=receipt_id,
            product_id=request.product_id,
            quantity=validated_deal.quantity,
            effective_unit_price=validated_deal.effective_unit_price,
            total_payable_amount=validated_deal.total_payable_amount,
            key_id=None,
            is_simulated=True,
            message="Razorpay Order created in simulation fallback mode (credentials not configured).",
        )

    @classmethod
    def verify_payment_safe(
        cls,
        session_id: str,
        order_id: str,
        payment_id: str,
        signature: str,
        session: Optional["SessionState"] = None,
        secret: Optional[str] = None,
    ) -> RazorpayVerificationResponse:
        """
        Cryptographically verifies Razorpay payment callback using server-side HMAC SHA-256.
        Only transitions state to PAYMENT_CAPTURED and ESCROW_RESERVED when the signature is valid
        and matching a valid pre-existing deal.
        """
        # 1. State Gate: Ensure a valid active session and validated deal exist
        if not session or not session.last_validated_deal or not session.last_validated_deal.is_valid:
            raise ValueError("PAYMENT VERIFICATION FAILED: No validated deal found for session.")

        # 2. Signature Gate: Verify server-side HMAC SHA-256 signature
        if not cls.verify_payment_signature(order_id, payment_id, signature, secret=secret):
            raise ValueError("PAYMENT VERIFICATION FAILED: Cryptographic HMAC SHA-256 signature mismatch.")

        # 3. Transition Payment Lifecycle State Machine:
        # VALIDATED_DEAL -> ORDER_CREATED -> RAZORPAY_CHECKOUT -> SERVER-SIDE HMAC VERIFICATION -> PAYMENT_CAPTURED -> ESCROW_RESERVED
        validated_deal = session.last_validated_deal
        total_paisa = int(validated_deal.total_payable_amount * Decimal("100"))

        return RazorpayVerificationResponse(
            success=True,
            payment_status="PAYMENT_CAPTURED",
            escrow_status="ESCROW_RESERVED",
            order_id=order_id,
            payment_id=payment_id,
            session_id=session_id,
            amount_in_paisa=total_paisa,
            currency="INR",
            effective_unit_price=validated_deal.effective_unit_price,
            total_payable_amount=validated_deal.total_payable_amount,
            quantity=validated_deal.quantity,
            message="Payment cryptographically verified. Funds captured and held in Authenticity Escrow.",
        )

