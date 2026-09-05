import sys
from decimal import Decimal

from app.orchestrator import AgentOrchestrator
from app.data_loader import db
from app.session_manager import session_db


def test_bug1_quantity_savings_consistency():
    """
    Bug 1: Asking savings question during active quantity deal must NOT re-discount
    or clamp to floor price. Must preserve active offer and compute exact savings.
    """
    sid = "sess_reg_bug1"
    pid = "prod_003"  # Listed price 2500, reservation 1550

    # Step 1-5: Negotiate single unit down to 2150 (Round 5)
    AgentOrchestrator.process_user_message(sid, pid, "Can you give me some discount?")
    AgentOrchestrator.process_user_message(sid, pid, "Can you do 1800?")
    AgentOrchestrator.process_user_message(sid, pid, "Best price?")
    AgentOrchestrator.process_user_message(sid, pid, "What is the best for one piece?")
    res_r5 = AgentOrchestrator.process_user_message(sid, pid, "Can you reduce it a little more?")
    assert res_r5.validated_deal.effective_unit_price == Decimal("2150.00")

    # Step 6: Switch to 5 units
    res_qty5 = AgentOrchestrator.process_user_message(sid, pid, "Actually, what if I take 5 pieces?")
    assert res_qty5.quantity == 5
    assert res_qty5.validated_deal.effective_unit_price == Decimal("1763.00")
    assert res_qty5.validated_deal.total_payable_amount == Decimal("8815.00")
    assert res_qty5.can_show_payment is False

    # Step 7: Ask savings question
    res_savings = AgentOrchestrator.process_user_message(
        sid, pid, "So how much am I saving compared with buying 5 at the normal price?"
    )
    # MUST NOT change unit price to 1550 or total to 7750
    assert res_savings.quantity == 5
    assert res_savings.validated_deal.effective_unit_price == Decimal("1763.00"), f"Expected 1763.00, got {res_savings.validated_deal.effective_unit_price}"
    assert res_savings.validated_deal.total_payable_amount == Decimal("8815.00"), f"Expected 8815.00, got {res_savings.validated_deal.total_payable_amount}"
    assert res_savings.can_show_payment is False
    assert res_savings.deal_status == "negotiating"
    # Verify savings amount in response text
    assert "1,935" in res_savings.message or "1935" in res_savings.message
    assert "10,750" in res_savings.message or "10750" in res_savings.message
    print("[PASS] Bug 1: Quantity price and savings consistency verified!")


def test_bug2_quantity_deal_acceptance():
    """
    Bug 2: Acceptance of active quantity deal ('Okay, I'll take all 5' or 'yes')
    must validate cleanly, set deal_status='agreed', and can_show_payment=True.
    """
    sid = "sess_reg_bug2"
    pid = "prod_003"

    # Reach 2150 single-unit negotiated anchor then switch to 5 pieces
    AgentOrchestrator.process_user_message(sid, pid, "Can you give me some discount?")
    AgentOrchestrator.process_user_message(sid, pid, "Can you do 1800?")
    AgentOrchestrator.process_user_message(sid, pid, "Best price?")
    AgentOrchestrator.process_user_message(sid, pid, "What is the best for one piece?")
    AgentOrchestrator.process_user_message(sid, pid, "Can you reduce it a little more?")
    res_qty = AgentOrchestrator.process_user_message(sid, pid, "What if I take 5 pieces?")
    assert res_qty.validated_deal.effective_unit_price == Decimal("1763.00")
    assert res_qty.validated_deal.total_payable_amount == Decimal("8815.00")

    # Accept all 5
    res_accept = AgentOrchestrator.process_user_message(sid, pid, "Okay, I'll take all 5.")
    assert res_accept.can_show_payment is True, "can_show_payment must be True"
    assert res_accept.deal_status == "agreed", f"deal_status must be 'agreed', got {res_accept.deal_status}"
    assert res_accept.quantity == 5
    assert res_accept.validated_deal.effective_unit_price == Decimal("1763.00")
    assert res_accept.validated_deal.total_payable_amount == Decimal("8815.00")

    # Also test contextual 'yes' on a separate session
    sid_yes = "sess_reg_bug2_yes"
    AgentOrchestrator.process_user_message(sid_yes, pid, "Can you give me some discount?")
    AgentOrchestrator.process_user_message(sid_yes, pid, "Can you do 1800?")
    AgentOrchestrator.process_user_message(sid_yes, pid, "Best price?")
    AgentOrchestrator.process_user_message(sid_yes, pid, "What is the best for one piece?")
    AgentOrchestrator.process_user_message(sid_yes, pid, "Can you reduce it a little more?")
    AgentOrchestrator.process_user_message(sid_yes, pid, "What if I take 5 pieces?")
    res_yes = AgentOrchestrator.process_user_message(sid_yes, pid, "yes")
    assert res_yes.can_show_payment is True
    assert res_yes.deal_status == "agreed"
    assert res_yes.quantity == 5
    assert res_yes.validated_deal.effective_unit_price == Decimal("1763.00")
    assert res_yes.validated_deal.total_payable_amount == Decimal("8815.00")
    print("[PASS] Bug 2: Quantity deal acceptance & payment trigger verified!")


def test_bug3_durability_question_routing():
    """
    Bug 3: 'How durable is it?' must route to Product Q&A, NOT price negotiation.
    Must NOT produce a price counter.
    """
    sid = "sess_reg_bug3"
    pid = "prod_003"

    res = AgentOrchestrator.process_user_message(sid, pid, "How durable is it?")
    assert res.intent in ["product_question", "trust_hesitation", "trust_concern"], f"Unexpected intent: {res.intent}"
    assert res.negotiation_round == 0, f"Expected round 0, got {res.negotiation_round}"
    assert res.can_show_payment is False
    assert "I can do" not in res.message
    assert "best rate" not in res.message.lower()
    assert "durability" in res.message.lower()
    print("[PASS] Bug 3: Durability question correctly routed to Product Q&A!")


def test_bug4_media_vs_detail_separation_and_missing_specs():
    """
    Bug 4:
    - Product detail questions return evidence_items = [] and clean text without internal IDs.
    - Explicit media questions return only matching media items.
    - Missing specs (GSM, durability rating) are reported honestly.
    """
    pid = "prod_003"

    # Detail question -> 0 evidence items
    res_mat = AgentOrchestrator.process_user_message("sess_reg_bug4_mat", pid, "What exactly is the material?")
    assert len(res_mat.evidence_items) == 0, f"Expected 0 evidence items, got {len(res_mat.evidence_items)}"
    assert "• [" not in res_mat.message, "Internal evidence item bullet must not be in user text"

    # Durability question -> 0 evidence items
    res_dur = AgentOrchestrator.process_user_message("sess_reg_bug4_dur", pid, "How durable is it?")
    assert len(res_dur.evidence_items) == 0

    # Missing GSM specification -> honest response
    res_gsm = AgentOrchestrator.process_user_message("sess_reg_bug4_gsm", pid, "What is the GSM?")
    assert "don't have the gsm specification" in res_gsm.message.lower()
    assert len(res_gsm.evidence_items) == 0

    # Explicit photo request -> image evidence only
    res_photo = AgentOrchestrator.process_user_message("sess_reg_bug4_photo", pid, "Show me photos")
    assert len(res_photo.evidence_items) > 0
    assert all(e["type"] == "image" for e in res_photo.evidence_items)

    # Explicit video request on prod_008 (jacket) -> video evidence only
    res_video = AgentOrchestrator.process_user_message("sess_reg_bug4_vid", "prod_008", "Can I see a video?")
    assert len(res_video.evidence_items) > 0
    assert all(e["type"] == "video" for e in res_video.evidence_items)

    # Combined photo and video request on prod_008 -> both types
    res_both = AgentOrchestrator.process_user_message("sess_reg_bug4_both", "prod_008", "Show me photos and video")
    assert any(e["type"] == "image" for e in res_both.evidence_items)
    assert any(e["type"] == "video" for e in res_both.evidence_items)

    print("[PASS] Bug 4: Media vs Detail separation and honest missing specs verified!")


if __name__ == "__main__":
    test_bug1_quantity_savings_consistency()
    test_bug2_quantity_deal_acceptance()
    test_bug3_durability_question_routing()
    test_bug4_media_vs_detail_separation_and_missing_specs()
    print("\n[SUCCESS] ALL PRE-SUBMISSION REGRESSION TESTS PASSED 100%!")

