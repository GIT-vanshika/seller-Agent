from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

EvidenceType = Literal["image", "video", "review", "text"]
EvidenceSource = Literal["seller_marketing", "seller_reality", "customer_experience"]


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    listed_price: Decimal = Field(..., ge=Decimal("0"), description="Public listed price (MRP)")
    category: str


class EvidenceResponse(BaseModel):
    id: str
    product_id: str
    type: EvidenceType = Field(..., description="Evidence type")
    source: EvidenceSource = Field(..., description="Restricted evidence source category")
    label: str
    content: str


class ProductListResponse(BaseModel):
    products: List[ProductResponse]


class ProductDetailResponse(BaseModel):
    product: ProductResponse
    evidence: List[EvidenceResponse]


class ChatApiRequest(BaseModel):
    session_id: Optional[str] = None
    product_id: str
    message: str = Field(..., min_length=1)


class ValidateDealApiRequest(BaseModel):
    session_id: str
    product_id: str
    quantity: int = Field(..., gt=0)
    proposed_unit_price: Decimal = Field(..., ge=Decimal("0"))


class CreateOrderApiRequest(BaseModel):
    session_id: str
    product_id: str
    quantity: int = Field(..., gt=0)
    requested_unit_price: Decimal = Field(..., ge=Decimal("0"))
    total_payable_amount: Decimal = Field(..., ge=Decimal("0"))


class VerifyPaymentApiRequest(BaseModel):
    session_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentApiResponse(BaseModel):
    success: bool
    payment_status: str
    escrow_status: str
    order_id: str
    payment_id: str
    session_id: str
    amount_in_paisa: int
    currency: str
    effective_unit_price: Decimal
    total_payable_amount: Decimal
    quantity: Optional[int] = 1
    message: str

