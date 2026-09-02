from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

# ==============================================================================
# 1. CONVERSATION CONTRACT
# ==============================================================================
ConversationRole = Literal["user", "assistant"]


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ConversationRole = Field(..., description="Role in buyer-facing conversation")
    content: str = Field(..., min_length=1, description="Non-empty text content of message")


class ConversationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    product_id: str = Field(..., min_length=1, description="Product identifier")
    messages: List[ConversationMessage] = Field(default_factory=list, description="Ordered buyer-facing chat history")


# ==============================================================================
# 2. INTENT & HESITATION UNDERSTANDING CONTRACT
# ==============================================================================
PrimaryIntent = Literal[
    "product_question",
    "trust_concern",
    "price_negotiation",
    "purchase_intent",
    "clarification",
    "general_conversation",
]

HesitationType = Literal["trust", "price", "both", "none"]


class ProductQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=500, description="Normalized product inquiry question")


class BuyerIntentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_intent: PrimaryIntent = Field(..., description="Primary classification of buyer input")
    hesitation: HesitationType = Field(..., description="Categorization of buyer hesitation state")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score bounded between 0.0 and 1.0")
    reason: str = Field(..., min_length=1, max_length=500, description="Short classification reasoning")
    product_question: Optional[ProductQuestion] = Field(default=None, description="Optional structured product question")


# Legacy alias for backward compatibility during contract transition
HesitationDecision = BuyerIntentDecision


# ==============================================================================
# 3. AGENT WORKFLOW DECISION CONTRACT
# ==============================================================================
AgentAction = Literal[
    "ask_clarification",
    "resolve_trust",
    "negotiate_price",
    "resolve_trust_then_negotiate",
    "provide_information",
    "end_conversation",
]


class AgentActionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: AgentAction = Field(..., description="Controlled high-level workflow action decision")
    reason: str = Field(..., min_length=1, max_length=500, description="Reasoning for workflow action decision")


# ==============================================================================
# 4. TRUST STATE CONTRACT
# ==============================================================================
TrustStatus = Literal["unresolved", "partially_resolved", "resolved", "insufficient_evidence"]


class TrustState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TrustStatus = Field(default="unresolved", description="Controlled resolution status of product quality/trust")
    last_evidence_ids_used: List[str] = Field(default_factory=list, description="Traceable evidence item IDs displayed to buyer")


# ==============================================================================
# 5. NEGOTIATION STATE CONTRACT
# ==============================================================================
NegotiationStatus = Literal["idle", "negotiating", "agreed", "rejected", "exceeded_rounds"]


class NegotiationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool = Field(default=False, description="Whether price negotiation is active")
    round_number: int = Field(default=0, ge=0, description="Completed negotiation rounds")
    quantity: int = Field(default=1, gt=0, description="Quantity being negotiated")
    last_buyer_offer: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Last buyer proposed unit price")
    last_seller_counter: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Last seller proposed counter price")
    seller_authorized_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Current seller authorized price from PolicyEngine")
    status: NegotiationStatus = Field(default="idle", description="Controlled negotiation status")


# ==============================================================================
# 6. TRANSACTION STATE CONTRACT
# ==============================================================================
TransactionStatus = Literal["not_ready", "deal_proposed", "validated", "order_created", "completed", "failed"]


class TransactionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TransactionStatus = Field(default="not_ready", description="Controlled transaction/checkout state")
    proposed_unit_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Session proposed unit price")
    validated_unit_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Validated unit price from DealConsistencyValidator")
    total_payable_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0"), description="Validated total transaction value")
    validated_deal_id: Optional[str] = Field(default=None, description="ID of validated deal")
    razorpay_order_id: Optional[str] = Field(default=None, description="Generated Razorpay order ID post-validation")


# ==============================================================================
# 7. AGENT SESSION CONTRACT (COMPOSITE BOUNDED STATE)
# ==============================================================================
class AgentSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    product_id: str = Field(..., min_length=1, description="Product identifier")
    conversation: ConversationState = Field(..., description="Bounded conversation state")
    intent_decision: Optional[BuyerIntentDecision] = Field(default=None, description="Latest buyer intent & hesitation decision")
    action_decision: Optional[AgentActionDecision] = Field(default=None, description="Latest workflow action decision")
    trust: TrustState = Field(default_factory=TrustState, description="Bounded trust state")
    negotiation: NegotiationState = Field(default_factory=NegotiationState, description="Bounded negotiation state")
    transaction: TransactionState = Field(default_factory=TransactionState, description="Bounded transaction state")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
