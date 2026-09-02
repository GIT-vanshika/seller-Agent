import uuid
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel
from app.deal_validator import DealConsistencyValidator, ValidatedDeal, DealValidationRequest
from app.policy_engine import PolicyEngine, PolicyEngineDecision
from app.models import SellerPolicy


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
    message: str


class RazorpayService:
    """
    Pre-Checkout Razorpay Order Creation Service.
    Determines final payable amount ONLY by executing PolicyEngine & DealConsistencyValidator on the backend control plane.
    Rejects any unvalidated, tampered, or invalid deal requests.
    """

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

        # Check 1: Deal MUST be authorized by PolicyEngine AND valid by DealConsistencyValidator
        if not decision.accepted or not validated_deal.is_valid:
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
        order_id = f"order_rzp_{uuid.uuid4().hex[:12]}"
        receipt_id = f"rcpt_{request.session_id}_{uuid.uuid4().hex[:6]}"

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
            message="Razorpay Order created successfully after deterministic pre-checkout validation.",
        )
