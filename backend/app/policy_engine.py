from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel, Field
from app.models import SellerPolicy, PricingMode


class PolicyEngineDecision(BaseModel):
    accepted: bool
    seller_authorized_price: Decimal
    round_number: int
    max_rounds: int
    pricing_mode: PricingMode
    applied_tier_discount: Optional[Decimal] = None
    buyer_safe_explanation: str


class PolicyEngine:
    """
    Deterministic backend decision & concession engine.
    Calculates exact seller-authorized counter-offers and acceptance criteria based on SellerPolicy.
    Enforces hard negotiation with controlled diminishing concessions and zero capitulation on Round 1.
    """

    @classmethod
    def evaluate_offer(
        cls,
        policy: SellerPolicy,
        buyer_offer: Decimal,
        round_number: int = 1,
        quantity: int = 1,
    ) -> PolicyEngineDecision:
        listed_price = policy.listed_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        aspiration_price = policy.aspiration_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        target_price = policy.target_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        reservation_price = policy.reservation_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        offer = buyer_offer.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 1. Fixed Pricing Mode
        if policy.pricing_mode == "fixed":
            is_accepted = offer >= listed_price
            return PolicyEngineDecision(
                accepted=is_accepted,
                seller_authorized_price=listed_price,
                round_number=0,
                max_rounds=0,
                pricing_mode="fixed",
                buyer_safe_explanation=f"Product is listed under a fixed price of ₹{listed_price:.2f}.",
            )

        # 2. Negotiable Pricing Mode
        max_rounds = policy.max_negotiation_rounds

        # Check Bulk Tier baseline if applicable
        bulk_tier_discount = None
        bulk_baseline_unit_price = listed_price
        if policy.bulk_rules and policy.bulk_rules.tiers:
            sorted_tiers = sorted(policy.bulk_rules.tiers, key=lambda t: t.min_quantity, reverse=True)
            for tier in sorted_tiers:
                if quantity >= tier.min_quantity:
                    bulk_tier_discount = tier.discount_percentage
                    multiplier = Decimal("1.0") - (tier.discount_percentage / Decimal("100.0"))
                    bulk_baseline_unit_price = (listed_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    break

        # Adjust top anchor for bulk order if bulk baseline is lower than listed
        effective_anchor = min(aspiration_price, bulk_baseline_unit_price)

        # Exceeded Max Rounds Check
        if round_number > max_rounds:
            # Hold firm at target_price
            final_firm_price = max(target_price, reservation_price)
            if offer >= final_firm_price:
                return PolicyEngineDecision(
                    accepted=True,
                    seller_authorized_price=offer,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=bulk_tier_discount,
                    buyer_safe_explanation=f"Offer of ₹{offer:.2f} meets the final negotiation threshold.",
                )
            else:
                return PolicyEngineDecision(
                    accepted=False,
                    seller_authorized_price=final_firm_price,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=bulk_tier_discount,
                    buyer_safe_explanation=f"Maximum negotiation rounds ({max_rounds}) reached. Our final firm offer is ₹{final_firm_price:.2f}.",
                )

        # Diminishing Concession Math with Normalized Decay Factor
        concession_span = effective_anchor - target_price
        if concession_span <= Decimal("0.00") or max_rounds <= 0:
            seller_step_price = target_price
        else:
            max_decay = Decimal("1.0") - (Decimal("0.55") ** max_rounds)
            current_decay = Decimal("1.0") - (Decimal("0.55") ** min(round_number, max_rounds))
            decay_factor = current_decay / max_decay if max_decay > Decimal("0.00") else Decimal("1.0")
            calculated_step = effective_anchor - (concession_span * decay_factor)
            seller_step_price = max(calculated_step, target_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Evaluate Offer against Seller Authorized Step Price
        if offer >= seller_step_price:
            return PolicyEngineDecision(
                accepted=True,
                seller_authorized_price=offer,
                round_number=round_number,
                max_rounds=max_rounds,
                pricing_mode="negotiable",
                applied_tier_discount=bulk_tier_discount,
                buyer_safe_explanation=f"Offer of ₹{offer:.2f} accepted in round {round_number}.",
            )
        else:
            return PolicyEngineDecision(
                accepted=False,
                seller_authorized_price=seller_step_price,
                round_number=round_number,
                max_rounds=max_rounds,
                pricing_mode="negotiable",
                applied_tier_discount=bulk_tier_discount,
                buyer_safe_explanation=f"Offer of ₹{offer:.2f} is below acceptable commercial threshold. Proposed counter-offer is ₹{seller_step_price:.2f}.",
            )
