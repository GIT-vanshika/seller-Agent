import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models import SellerPolicy, PricingMode


class DealValidationRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, description="Quantity of items being purchased")
    proposed_unit_price: Decimal = Field(..., ge=Decimal("0"), description="Buyer proposed unit price")
    seller_authorized_price: Decimal = Field(..., ge=Decimal("0"), description="Seller-authorized unit price from PolicyEngine")
    current_negotiated_unit_price: Optional[Decimal] = Field(
        default=None, ge=Decimal("0"), description="Previously agreed negotiated unit price in active session"
    )
    negotiation_round: int = Field(default=1, ge=0, description="Current negotiation round")
    buyer_committed: bool = Field(default=False, description="Whether buyer explicitly committed to purchase")


class ValidatedDeal(BaseModel):
    deal_id: str
    product_id: str
    quantity: int
    listed_price: Decimal
    proposed_unit_price: Decimal
    effective_unit_price: Decimal
    total_payable_amount: Decimal
    pricing_mode: PricingMode
    is_valid: bool
    validation_code: str
    validation_message: str
    applied_rule_description: str


class DealConsistencyValidator:
    """
    Single deterministic authority that validates deal terms BEFORE any Razorpay order is created.
    Validates seller-authorized deal terms against SellerPolicy without leaking private policy parameters.
    Enforces explicit pricing-path traceability: final price must be authorized by PolicyEngine, bulk rules, or catalog price.
    """

    @staticmethod
    def _calculate_bulk_unit_price(
        policy: SellerPolicy,
        quantity: int,
        base_unit_price: Optional[Decimal] = None,
    ) -> Optional[Decimal]:
        if not policy.bulk_rules or not policy.bulk_rules.tiers:
            return None

        applicable_tier = None
        sorted_tiers = sorted(policy.bulk_rules.tiers, key=lambda t: t.min_quantity, reverse=True)
        for tier in sorted_tiers:
            if quantity >= tier.min_quantity:
                applicable_tier = tier
                break

        if applicable_tier:
            anchor = (base_unit_price or policy.listed_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            multiplier = Decimal("1.0") - (applicable_tier.discount_percentage / Decimal("100.0"))
            bulk_unit_price = (policy.listed_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            bulk_unit_price = (anchor * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return bulk_unit_price

        return None

    @classmethod
    def validate_deal(cls, policy: SellerPolicy, request: DealValidationRequest) -> ValidatedDeal:
        listed_price = policy.listed_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        reservation_price = policy.reservation_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        proposed_price = request.proposed_unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        authorized_price = request.seller_authorized_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        quantity = request.quantity
        deal_id = f"deal_{uuid.uuid4().hex[:10]}"

        # Rule 1: Validate Quantity Floor
        if quantity <= 0:
            return ValidatedDeal(
                deal_id=deal_id,
                product_id=policy.product_id,
                quantity=quantity,
                listed_price=listed_price,
                proposed_unit_price=proposed_price,
                effective_unit_price=listed_price,
                total_payable_amount=Decimal("0.00"),
                pricing_mode=policy.pricing_mode,
                is_valid=False,
                validation_code="INVALID_QUANTITY",
                validation_message="Quantity must be greater than zero.",
                applied_rule_description="Quantity floor rule.",
            )

        # Rule 2: Validate Fixed Pricing Mode
        if policy.pricing_mode == "fixed":
            if proposed_price != listed_price:
                return ValidatedDeal(
                    deal_id=deal_id,
                    product_id=policy.product_id,
                    quantity=quantity,
                    listed_price=listed_price,
                    proposed_unit_price=proposed_price,
                    effective_unit_price=listed_price,
                    total_payable_amount=(listed_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    pricing_mode=policy.pricing_mode,
                    is_valid=False,
                    validation_code="FIXED_PRICE_VIOLATION",
                    validation_message=f"Product is sold at a fixed price of ₹{listed_price:.2f}. Price negotiation is disabled.",
                    applied_rule_description="Fixed pricing mode policy constraint.",
                )

        # Rule 3: Policy Boundary Enforcement (Rounds >= Max Rounds)
        if policy.pricing_mode == "negotiable" and request.negotiation_round >= policy.max_negotiation_rounds:
            firm_target = authorized_price
            if proposed_price < firm_target and not request.buyer_committed:
                return ValidatedDeal(
                    deal_id=deal_id,
                    product_id=policy.product_id,
                    quantity=quantity,
                    listed_price=listed_price,
                    proposed_unit_price=proposed_price,
                    effective_unit_price=firm_target,
                    total_payable_amount=(firm_target * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    pricing_mode=policy.pricing_mode,
                    is_valid=False,
                    validation_code="SELLER_POLICY_FLOOR",
                    validation_message=f"We cannot get below ₹{firm_target:.2f}. It is against seller policy.",
                    applied_rule_description="Seller pricing policy constraint.",
                )

        # Rule 4: Seller Reservation Floor Safety Check (Internal Security Boundary)
        if proposed_price < reservation_price or authorized_price < reservation_price:
            return ValidatedDeal(
                deal_id=deal_id,
                product_id=policy.product_id,
                quantity=quantity,
                listed_price=listed_price,
                proposed_unit_price=proposed_price,
                effective_unit_price=authorized_price,
                total_payable_amount=(authorized_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                pricing_mode=policy.pricing_mode,
                is_valid=False,
                validation_code="EXCEEDS_RESERVATION_FLOOR",
                validation_message="Proposed offer is below acceptable commercial range.",
                applied_rule_description="Seller policy pricing constraint.",
            )

        # Rule 5: Explicit Authorized Pricing Path Resolution (No arbitrary 'minimum candidate wins'!)
        bulk_unit_price = cls._calculate_bulk_unit_price(policy, quantity)

        # Determine the best valid authorized path
        authorized_paths = []

        if quantity == 1:
            # Path A: PolicyEngine step concession authorization for single unit
            authorized_paths.append((authorized_price, "Negotiated Policy Concession"))
            # Path C: Standard catalog listed price
            authorized_paths.append((listed_price, "Standard Catalog Listed Price"))
        else:
            # Multi-unit volume deal: governed by authoritative volume tiers, not single-unit curve
            if bulk_unit_price is not None and bulk_unit_price >= reservation_price:
                authorized_paths.append((bulk_unit_price, f"Bulk Tier Pricing (Qty >= {quantity})"))
            # Multi-unit volume deal: anchored on negotiated unit price or listed price
            if request.current_negotiated_unit_price is not None:
                if request.current_negotiated_unit_price < reservation_price or request.current_negotiated_unit_price > listed_price:
                    return ValidatedDeal(
                        deal_id=deal_id,
                        product_id=policy.product_id,
                        quantity=quantity,
                        listed_price=listed_price,
                        proposed_unit_price=proposed_price,
                        effective_unit_price=listed_price,
                        total_payable_amount=Decimal("0.00"),
                        pricing_mode=policy.pricing_mode,
                        is_valid=False,
                        validation_code="CORRUPTED_ANCHOR",
                        validation_message="Negotiated anchor is outside valid policy boundaries.",
                        applied_rule_description="Negotiated anchor integrity rule.",
                    )
                unit_anchor = request.current_negotiated_unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif request.negotiation_round > 1:
                return ValidatedDeal(
                    deal_id=deal_id,
                    product_id=policy.product_id,
                    quantity=quantity,
                    listed_price=listed_price,
                    proposed_unit_price=proposed_price,
                    effective_unit_price=listed_price,
                    total_payable_amount=Decimal("0.00"),
                    pricing_mode=policy.pricing_mode,
                    is_valid=False,
                    validation_code="MISSING_NEGOTIATED_ANCHOR",
                    validation_message="Missing negotiated unit price anchor in existing negotiated session.",
                    applied_rule_description="Negotiated anchor integrity rule.",
                )
            else:
                authorized_paths.append((listed_price, "Standard Catalog Listed Price"))
                unit_anchor = listed_price

            bulk_unit_price = cls._calculate_bulk_unit_price(policy, quantity, base_unit_price=unit_anchor)
            if bulk_unit_price is not None:
                clamped_bulk = max(bulk_unit_price, reservation_price)
                authorized_paths.append((clamped_bulk, f"Bulk Tier Pricing (Qty >= {quantity})"))
            else:
                authorized_paths.append((unit_anchor, f"Volume Base Anchor (Qty {quantity})"))

        # Select the lowest unit price strictly authorized by backend pricing paths
        best_authorized_price, applied_path_desc = min(authorized_paths, key=lambda p: p[0])

        # Rule 6: Validate proposed price against authorized path threshold
        if proposed_price < best_authorized_price:
            return ValidatedDeal(
                deal_id=deal_id,
                product_id=policy.product_id,
                quantity=quantity,
                listed_price=listed_price,
                proposed_unit_price=proposed_price,
                effective_unit_price=best_authorized_price,
                total_payable_amount=(best_authorized_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                pricing_mode=policy.pricing_mode,
                is_valid=False,
                validation_code="OFFER_BELOW_SELLER_THRESHOLD",
                validation_message="Proposed offer is below acceptable commercial threshold for this round.",
                applied_rule_description=f"Authorized threshold rule: {applied_path_desc}.",
            )

        effective_unit_price = min(proposed_price, best_authorized_price)
        total_payable = (effective_unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return ValidatedDeal(
            deal_id=deal_id,
            product_id=policy.product_id,
            quantity=quantity,
            listed_price=listed_price,
            proposed_unit_price=proposed_price,
            effective_unit_price=effective_unit_price,
            total_payable_amount=total_payable,
            pricing_mode=policy.pricing_mode,
            is_valid=True,
            validation_code="VALID_DEAL",
            validation_message="Deal terms validated successfully by Deal Consistency Validator.",
            applied_rule_description=applied_path_desc,
        )
