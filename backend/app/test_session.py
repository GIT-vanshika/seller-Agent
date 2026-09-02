from decimal import Decimal
from app.session_manager import session_db, SessionState
from app.contracts import BuyerIntentDecision, TrustState, AgentSession


def run_session_tests():
    print("==================================================================")
    print("     RUNNING STEP 2.4 CONVERSATION STATE / SESSION TEST SUITE     ")
    print("==================================================================")

    # 1. New Session Creation & Initial State
    session_id = "test_sess_001"
    product_id = "prod_003"
    s1 = session_db.get_or_create_session(session_id, product_id)
    assert s1.session_id == session_id
    assert s1.product_id == product_id
    assert s1.negotiation_round == 0
    assert s1.deal_status == "exploring"
    print("[PASS] Test 1: New session created with correct default bounded state.")

    # 2. Appending User & Assistant Messages
    session_db.append_message(session_id, sender="buyer", text="Hello, is this pure silk?")
    session_db.append_message(session_id, sender="agent", text="According to the seller catalog description...")
    s2 = session_db.get_session(session_id)
    assert len(s2.messages) == 2
    assert s2.messages[0].sender == "buyer"
    assert s2.messages[1].sender == "agent"
    print("[PASS] Test 2: User and assistant messages appended and preserved.")

    # 3. Preserving Intent, Negotiation, and Trust State across Turns
    s2.trust_state = TrustState(status="partially_resolved", last_evidence_ids_used=["ev_007"])
    session_db.record_negotiation_step(session_id, agreed_price=Decimal("2250.00"), quantity=2, increment_round=True)
    s3 = session_db.get_session(session_id)
    assert s3.negotiation_round == 1
    assert s3.quantity == 2
    assert s3.current_negotiated_unit_price == Decimal("2250.00")
    assert s3.deal_status == "agreed"
    assert s3.trust_state.status == "partially_resolved"
    print("[PASS] Test 3: Negotiation and Trust state correctly preserved across multi-turn steps.")

    # 4. Product Isolation Assertion (Reset if product changed in same session ID)
    s_iso = session_db.get_or_create_session(session_id, "prod_004")
    assert s_iso.product_id == "prod_004"
    assert s_iso.negotiation_round == 0
    assert len(s_iso.messages) == 0
    print("[PASS] Test 4: Cross-product isolation verified: switching product_id cleanly resets session state.")

    # 5. Invalid / Nonexistent Session ID Handling (Graceful fallback)
    s_invalid = session_db.get_or_create_session(None, "prod_001")
    assert s_invalid.session_id.startswith("sess_")
    assert s_invalid.product_id == "prod_001"
    print("[PASS] Test 5: Invalid/None session_id handled safely with fresh session creation.")

    # 6. Bounded History Limit Enforcement (Max 20 messages)
    s_bound = session_db.get_or_create_session("test_bound_sess", "prod_001")
    for i in range(25):
        session_db.append_message("test_bound_sess", sender="buyer", text=f"Message {i}")
    assert len(s_bound.messages) == 20
    assert s_bound.messages[-1].text == "Message 24"
    print("[PASS] Test 6: Bounded history limit enforced (capped at 20 messages).")

    # 7. AgentSession Structured Export Assertion (Zero SellerPolicy secrets)
    agent_sess: AgentSession = session_db.export_agent_session("test_bound_sess")
    sess_json = agent_sess.model_dump_json()
    assert "reservation_price" not in sess_json
    assert "target_price" not in sess_json
    assert "aspiration_price" not in sess_json
    assert "batna" not in sess_json
    print("[PASS] Test 7: Exported AgentSession verified: ZERO private SellerPolicy fields stored.")

    print("\n==================================================================")
    print("   [SUCCESS] ALL 7 SESSION & MULTI-TURN STATE TESTS PASSED!")
    print("==================================================================\n")


if __name__ == "__main__":
    run_session_tests()

