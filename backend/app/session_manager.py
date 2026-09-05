import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.deal_validator import ValidatedDeal
from app.contracts import (
    AgentSession,
    ConversationState,
    ConversationMessage,
    BuyerIntentDecision,
    AgentActionDecision,
    TrustState,
    NegotiationState,
    TransactionState,
)


class ChatMessage(BaseModel):
    sender: str  # "buyer" or "agent"
    text: str
    intent: Optional[str] = None
    suggested_price: Optional[Decimal] = None
    timestamp: str


class SessionState(BaseModel):
    session_id: str
    product_id: str
    quantity: int = 1
    negotiation_round: int = 0
    current_negotiated_unit_price: Optional[Decimal] = None
    single_unit_negotiated_price: Optional[Decimal] = None
    deal_status: str = "exploring"  # "exploring", "negotiating", "agreed", "checked_out"
    messages: List[ChatMessage] = Field(default_factory=list)
    last_validated_deal: Optional[ValidatedDeal] = None
    trust_state: Optional[TrustState] = None
    latest_intent_decision: Optional[BuyerIntentDecision] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionManager:
    """
    In-Memory Bounded Session & Conversation Context Manager.
    Supports multi-turn state preservation, product isolation, history bounds (max 20 messages),
    and structured Pydantic AgentSession exports.
    """

    MAX_HISTORY_MESSAGES = 20

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create_session(self, session_id: Optional[str], product_id: str) -> SessionState:
        now_str = datetime.now(timezone.utc).isoformat()
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            # CROSS-PRODUCT ISOLATION ASSERTION: Reset if product changed in same session ID
            if session.product_id != product_id:
                session = SessionState(
                    session_id=session_id,
                    product_id=product_id,
                    created_at=now_str,
                    updated_at=now_str,
                )
                self._sessions[session_id] = session
            return session

        new_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        session = SessionState(
            session_id=new_id,
            product_id=product_id,
            created_at=now_str,
            updated_at=now_str,
        )
        self._sessions[new_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def append_message(self, session_id: str, sender: str, text: str, intent: Optional[str] = None, suggested_price: Optional[Decimal] = None) -> SessionState:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        msg = ChatMessage(
            sender=sender,
            text=text,
            intent=intent,
            suggested_price=suggested_price,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.messages.append(msg)

        # BOUNDED HISTORY ENFORCEMENT: Keep context length bounded
        if len(session.messages) > self.MAX_HISTORY_MESSAGES:
            session.messages = session.messages[-self.MAX_HISTORY_MESSAGES:]

        session.updated_at = datetime.now(timezone.utc).isoformat()
        return session

    def record_negotiation_step(
        self,
        session_id: str,
        agreed_price: Optional[Decimal] = None,
        quantity: Optional[int] = None,
        increment_round: bool = True,
    ) -> SessionState:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        if increment_round:
            session.negotiation_round += 1

        if quantity is not None and quantity > 0:
            session.quantity = quantity

        if agreed_price is not None:
            session.current_negotiated_unit_price = agreed_price
            if session.quantity == 1:
                session.single_unit_negotiated_price = agreed_price
            session.deal_status = "agreed"
        elif session.negotiation_round > 0:
            session.deal_status = "negotiating"

        session.updated_at = datetime.now(timezone.utc).isoformat()
        return session

    def set_validated_deal(self, session_id: str, deal: ValidatedDeal, is_agreed: bool = True) -> SessionState:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        session.last_validated_deal = deal
        session.quantity = deal.quantity
        session.current_negotiated_unit_price = deal.effective_unit_price
        if deal.quantity == 1 and deal.is_valid:
            session.single_unit_negotiated_price = deal.effective_unit_price
        if deal.is_valid and is_agreed:
            session.deal_status = "agreed"
        elif session.negotiation_round > 0:
            session.deal_status = "negotiating"

        session.updated_at = datetime.now(timezone.utc).isoformat()
        return session

    def export_agent_session(self, session_id: str) -> AgentSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        conv_msgs = [
            ConversationMessage(
                role="user" if m.sender == "buyer" else "assistant",
                content=m.text,
            )
            for m in session.messages
        ]

        trust = session.trust_state or TrustState(status="unresolved", last_evidence_ids_used=[])

        neg_status = "idle"
        if session.deal_status == "agreed":
            neg_status = "agreed"
        elif session.deal_status == "negotiating":
            neg_status = "negotiating"

        neg_state = NegotiationState(
            active=(session.negotiation_round > 0),
            round_number=session.negotiation_round,
            quantity=session.quantity,
            last_seller_counter=session.current_negotiated_unit_price,
            seller_authorized_price=session.current_negotiated_unit_price,
            status=neg_status,
        )

        tx_status = "not_ready"
        val_price = None
        tot_amount = None
        val_id = None
        if session.last_validated_deal and session.last_validated_deal.is_valid:
            tx_status = "validated"
            val_price = session.last_validated_deal.effective_unit_price
            tot_amount = session.last_validated_deal.total_payable_amount
            val_id = session.last_validated_deal.deal_id

        tx_state = TransactionState(
            status=tx_status,
            proposed_unit_price=session.current_negotiated_unit_price,
            validated_unit_price=val_price,
            total_payable_amount=tot_amount,
            validated_deal_id=val_id,
        )

        return AgentSession(
            session_id=session.session_id,
            product_id=session.product_id,
            conversation=ConversationState(session_id=session.session_id, product_id=session.product_id, messages=conv_msgs),
            intent_decision=session.latest_intent_decision,
            action_decision=None,
            trust=trust,
            negotiation=neg_state,
            transaction=tx_state,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


# Global singleton session manager
session_db = SessionManager()
