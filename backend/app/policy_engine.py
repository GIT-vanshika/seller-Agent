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
        offer = buyer_offer.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if buyer_offer is not None else None

        # 1. Fixed Pricing Mode
        if policy.pricing_mode == "fixed":
            is_accepted = (offer >= listed_price) if offer is not None else False
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

        # 2a. Determine Bulk Tier Price if applicable
        bulk_tier_discount = None
        bulk_unit_price = None
        if policy.bulk_rules and policy.bulk_rules.tiers:
            sorted_tiers = sorted(policy.bulk_rules.tiers, key=lambda t: t.min_quantity, reverse=True)
            for tier in sorted_tiers:
                if quantity >= tier.min_quantity:
                    bulk_tier_discount = tier.discount_percentage
                    multiplier = Decimal("1.0") - (tier.discount_percentage / Decimal("100.0"))
                    bulk_unit_price = (listed_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    break

        # 2b. Determine Single-Unit Step Price for this round
        if policy.concession_schedule:
            # Policy-defined explicit schedule: protects exact authorized step prices
            idx = min(max(1, round_number), max_rounds) - 1
            single_unit_step = policy.concession_schedule[idx].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            # Dynamic convex Boulware curve: starts from listed_price anchor, concedes slowly at first
            span = listed_price - target_price
            if span <= Decimal("0.00") or max_rounds <= 0:
                single_unit_step = target_price
            else:
                # Convex progression: (round / max_rounds) ** 2
                # Concedes minimally early on, then increases concession toward deadline
                r_capped = min(max(1, round_number), max_rounds)
                progression = (Decimal(str(r_capped)) / Decimal(str(max_rounds))) ** 2
                single_unit_step = (listed_price - (span * progression)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        single_unit_step = max(single_unit_step, target_price, reservation_price)

        # 2c. Combine Single-Unit Step Price with Quantity Incentives
        if bulk_unit_price is not None:
            # If a quantity bulk tier applies, seller authorizes the better price between
            # the quantity tier price and the single-unit round concession price,
            # but strictly bounded above the reservation floor
            seller_step_price = max(min(single_unit_step, bulk_unit_price), reservation_price)
        else:
            seller_step_price = single_unit_step

        # 2d. Final Policy Boundary Check (Round >= Max Rounds)
        if round_number >= max_rounds:
            final_firm_price = seller_step_price
            if offer is not None and offer >= final_firm_price:
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
                    buyer_safe_explanation=f"We cannot get below ₹{final_firm_price:.2f}. It is against seller policy.",
                )

        # 2e. Evaluate Offer against Seller Authorized Step Price
        if offer is not None and offer >= seller_step_price:
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
                buyer_safe_explanation=f"Offer is below acceptable commercial threshold. Proposed counter-offer is ₹{seller_step_price:.2f}.",
            )
