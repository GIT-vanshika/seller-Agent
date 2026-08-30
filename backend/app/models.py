from decimal import Decimal
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, model_validator

# Controlled types
PricingMode = Literal["fixed", "negotiable"]
BATNAType = Literal["normal_sale", "hold_price", "another_channel"]
EvidenceType = Literal["image", "video", "review", "text"]
EvidenceSource = Literal["seller_marketing", "seller_reality", "customer_experience"]


class Product(BaseModel):
    id: str
    name: str
    description: str
    listed_price: Decimal = Field(..., ge=Decimal("0"), description="Non-negative listed price")
    category: str


class Evidence(BaseModel):
    id: str
    product_id: str
    type: EvidenceType = Field(..., description="Evidence type")
    source: EvidenceSource = Field(..., description="Restricted evidence source category")
    label: str
    content: str


class BulkTier(BaseModel):
    min_quantity: int = Field(..., gt=0, description="Minimum quantity required to trigger discount tier")
    discount_percentage: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("100"), description="Discount percentage for this tier"
    )


class BulkRule(BaseModel):
    tiers: List[BulkTier] = Field(..., min_length=1, description="List of bulk quantity discount tiers")


class SellerPolicy(BaseModel):
    product_id: str
    pricing_mode: PricingMode = Field(default="negotiable", description="Fixed or negotiable pricing mode")
    listed_price: Decimal = Field(..., ge=Decimal("0"), description="Non-negative listed price (MRP)")
    aspiration_price: Decimal = Field(..., ge=Decimal("0"), description="Aggressive opening anchor price")
    target_price: Decimal = Field(..., ge=Decimal("0"), description="Realistic preferred closing price")
    reservation_price: Decimal = Field(..., ge=Decimal("0"), description="Absolute lowest acceptable price (PRIVATE)")
    batna: BATNAType = Field(default="normal_sale", description="Best Alternative To a Negotiated Agreement")
    bulk_rules: Optional[BulkRule] = None
    max_negotiation_rounds: int = Field(..., ge=0, description="Max negotiation rounds (0 for fixed)")

    @model_validator(mode="after")
    def validate_pricing_consistency(self) -> "SellerPolicy":
        if self.pricing_mode == "fixed":
            if self.max_negotiation_rounds != 0:
                raise ValueError("max_negotiation_rounds must be 0 for fixed pricing mode")
            if not (self.reservation_price == self.target_price == self.aspiration_price == self.listed_price):
                raise ValueError("For fixed pricing, reservation, target, and aspiration prices must equal listed_price")
        elif self.pricing_mode == "negotiable":
            if self.max_negotiation_rounds <= 0:
                raise ValueError("max_negotiation_rounds must be greater than 0 for negotiable pricing mode")
            if self.reservation_price > self.target_price:
                raise ValueError("reservation_price cannot exceed target_price")
            if self.target_price > self.aspiration_price:
                raise ValueError("target_price cannot exceed aspiration_price")
            if self.aspiration_price > self.listed_price:
                raise ValueError("aspiration_price cannot exceed listed_price")

        # Validate that EVERY configured bulk tier respects the reservation price floor
        if self.bulk_rules is not None:
            for tier in self.bulk_rules.tiers:
                discount_multiplier = Decimal("1.0") - (tier.discount_percentage / Decimal("100.0"))
                discounted_unit_price = self.listed_price * discount_multiplier
                if discounted_unit_price < self.reservation_price:
                    raise ValueError(
                        f"Bulk tier (min_quantity={tier.min_quantity}, discount={tier.discount_percentage}%) "
                        f"results in unit price ({discounted_unit_price:.2f}) below reservation_price ({self.reservation_price:.2f})"
                    )

        return self


class NegotiationExperience(BaseModel):
    session_id: str
    product_id: str
    starting_price: Decimal = Field(..., ge=Decimal("0"), description="Opening price for the session")
    buyer_offers: List[Decimal] = Field(default_factory=list, description="Sequence of buyer offers")
    seller_counter_offers: List[Decimal] = Field(default_factory=list, description="Sequence of seller counter-offers")
    rounds: int = Field(..., ge=0, description="Number of negotiation rounds completed")
    final_agreed_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Agreed price if deal converted")
    converted: bool = Field(..., description="Whether the negotiation resulted in a sale")
    quantity: int = Field(default=1, gt=0, description="Quantity negotiated")
    seller_feedback: Optional[str] = Field(default=None, description="Seller notes/feedback on the session")
    buyer_feedback: Optional[str] = Field(default=None, description="Buyer notes/feedback on the session")
    successful_in_seller_view: Optional[bool] = Field(
        default=None, description="Whether seller considered the outcome successful"
    )
