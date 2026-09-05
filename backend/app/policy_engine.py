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
    nominal_tier_discount: Optional[Decimal] = None
    is_floor_clamped: bool = False
    unit_anchor: Optional[Decimal] = None
    total_payable_amount: Optional[Decimal] = None
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
        buyer_offer: Optional[Decimal],
        round_number: int = 1,
        quantity: int = 1,
        negotiated_unit_price: Optional[Decimal] = None,
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
                unit_anchor=listed_price,
                total_payable_amount=(listed_price * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                buyer_safe_explanation=f"Product is listed under a fixed price of ₹{listed_price:.2f}.",
            )

        # 2. Negotiable Pricing Mode
        max_rounds = policy.max_negotiation_rounds

        # -------------------------------------------------------------------------
        # CASE A: MULTI-UNIT / VOLUME DEAL (quantity > 1)
        # -------------------------------------------------------------------------
        # Commercial Rule:
        # - This is a volume deal.
        # - DO NOT multiply the 1-unit negotiated price (e.g. ₹900 × 2 ≠ ₹1800).
        # - DO NOT restart the 1-unit concession curve for multiple units.
        # - A volume deal invokes the authoritative seller policy volume tiers.
        # Formula:
        #   base_total = listed_price * quantity
        #   volume_discount = seller_policy(quantity)
        #   final_total = base_total - volume_discount
        #   effective_unit_price = final_total / quantity
        # Commercial Invariants:
        # 1. negotiated_unit_price <= listed_price
        # 2. No quantity transition may reset a valid negotiated anchor to listed_price.
        #    - Fresh session (round_number <= 1, no prior negotiation): listed_price is anchor.
        #    - Existing negotiated session: current_negotiated_unit_price is authoritative anchor.
        #    - If existing negotiated session (round_number > 1) unexpectedly has no anchor:
        #      fail safely rather than silently reverting to listed_price.
        # 3. Base subtotal = unit_anchor * quantity.
        # 4. If volume tier exists: final_total = base_subtotal * (1 - tier_discount) subject to seller floor.
        # 5. Effective unit price = final_total / quantity >= reservation_price.
        # 6. If floor clamped, do NOT claim nominal discount percentage and NEVER reveal seller floor.
        # -------------------------------------------------------------------------
        if quantity > 1:
            if negotiated_unit_price is not None:
                if negotiated_unit_price < reservation_price or negotiated_unit_price > listed_price:
                    raise ValueError(
                        f"CORRUPTED NEGOTIATION ANCHOR: Negotiated price ₹{negotiated_unit_price:.2f} "
                        f"is outside valid policy bounds [₹{reservation_price:.2f}, ₹{listed_price:.2f}]."
                    )
                unit_anchor = negotiated_unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif round_number > 1:
                # Existing negotiated session must not silently reset to listed_price
                raise ValueError("CORRUPTED NEGOTIATION STATE: Missing negotiated unit price anchor in existing negotiated session.")
            else:
                unit_anchor = listed_price

            bulk_tier_discount = None
            if policy.bulk_rules and policy.bulk_rules.tiers:
                sorted_tiers = sorted(policy.bulk_rules.tiers, key=lambda t: t.min_quantity, reverse=True)
                for tier in sorted_tiers:
                    if quantity >= tier.min_quantity:
                        bulk_tier_discount = tier.discount_percentage
                        break

            base_total = (listed_price * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_total = (unit_anchor * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if bulk_tier_discount is not None:
                discount_amt = (base_total * bulk_tier_discount / Decimal("100.0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                final_total = base_total - discount_amt
                effective_unit_price = (final_total / Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                raw_final_total = base_total - discount_amt
                raw_effective_unit_price = (raw_final_total / Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                effective_unit_price = listed_price
                final_total = base_total
                raw_final_total = base_total
                raw_effective_unit_price = unit_anchor

            effective_unit_price = max(effective_unit_price, reservation_price)
            # Floor protection check
            is_floor_clamped = False
            if raw_effective_unit_price < reservation_price:
                effective_unit_price = reservation_price
                final_total = (effective_unit_price * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                is_floor_clamped = True
                # Truthful commercial presentation: do not claim nominal discount if clamped by policy
                applied_tier_discount = None
            else:
                effective_unit_price = raw_effective_unit_price
                final_total = raw_final_total
                applied_tier_discount = bulk_tier_discount

            if offer is not None and offer >= effective_unit_price:
                return PolicyEngineDecision(
                    accepted=True,
                    seller_authorized_price=offer,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=applied_tier_discount,
                    nominal_tier_discount=bulk_tier_discount,
                    is_floor_clamped=is_floor_clamped,
                    unit_anchor=unit_anchor,
                    total_payable_amount=final_total,
                    buyer_safe_explanation=f"Offer of ₹{offer:.2f} meets the volume pricing threshold for {quantity} units.",
                )
            else:
                return PolicyEngineDecision(
                    accepted=False,
                    seller_authorized_price=effective_unit_price,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=applied_tier_discount,
                    nominal_tier_discount=bulk_tier_discount,
                    is_floor_clamped=is_floor_clamped,
                    unit_anchor=unit_anchor,
                    total_payable_amount=final_total,
                    buyer_safe_explanation=f"Volume authorized price is ₹{effective_unit_price:.2f}/unit for {quantity} units.",
                )

        # -------------------------------------------------------------------------
        # CASE B: SINGLE-UNIT NEGOTIATION (quantity == 1)
        # -------------------------------------------------------------------------
        # Determine Single-Unit Step Price for this round
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
        seller_step_price = single_unit_step

        # Final Policy Boundary Check (Round >= Max Rounds)
        if round_number >= max_rounds:
            final_firm_price = seller_step_price
            if offer is not None and offer >= final_firm_price:
                return PolicyEngineDecision(
                    accepted=True,
                    seller_authorized_price=offer,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=None,
                    buyer_safe_explanation=f"Offer of ₹{offer:.2f} meets the final negotiation threshold.",
                )
            else:
                return PolicyEngineDecision(
                    accepted=False,
                    seller_authorized_price=final_firm_price,
                    round_number=round_number,
                    max_rounds=max_rounds,
                    pricing_mode="negotiable",
                    applied_tier_discount=None,
                    buyer_safe_explanation=f"We cannot get below ₹{final_firm_price:.2f}. It is against seller policy.",
                )

        # Evaluate Offer against Seller Authorized Step Price
        if offer is not None and offer >= seller_step_price:
            return PolicyEngineDecision(
                accepted=True,
                seller_authorized_price=offer,
                round_number=round_number,
                max_rounds=max_rounds,
                pricing_mode="negotiable",
                applied_tier_discount=None,
                buyer_safe_explanation=f"Offer of ₹{offer:.2f} accepted in round {round_number}.",
            )
        else:
            return PolicyEngineDecision(
                accepted=False,
                seller_authorized_price=seller_step_price,
                round_number=round_number,
                max_rounds=max_rounds,
                pricing_mode="negotiable",
                applied_tier_discount=None,
                buyer_safe_explanation=f"Offer is below acceptable commercial threshold. Proposed counter-offer is ₹{seller_step_price:.2f}.",
            )
