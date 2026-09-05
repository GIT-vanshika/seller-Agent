import os
from decimal import Decimal
from app.orchestrator import AgentOrchestrator
from app.data_loader import db
from app.policy_engine import PolicyEngine, PolicyEngineDecision
from app.deal_validator import DealConsistencyValidator, DealValidationRequest
from app.razorpay_service import RazorpayService, RazorpayOrderRequest
from app.experience_store import experience_store
from app.session_manager import session_db


def test_final_mvp_hardening():
    print('\n' + '=' * 60)
    print('      FINAL MVP HARDENING COMPREHENSIVE SUITE')
    print('=' * 60)

    # ----------------------------------------------------
    # TEST 1: QUANTITIES 1, 2, 3, 4, 5 ON PROD_004 WITH NEGOTIATED ANCHOR 900
    # ----------------------------------------------------
    print('\n--- TEST 1: Quantities 1 to 5 with Negotiated Anchor 900 ---')
    sid_p4 = 'sess_mvp_quantities_p4'
    # Reach final firm price of 900 on prod_004 (7 rounds)
    for r in range(1, 8):
        AgentOrchestrator.process_user_message(sid_p4, 'prod_004', f'Can I get for 800 round {r}?')

    session = session_db.get_session(sid_p4)
    assert session.negotiation_round == 7
    assert session.single_unit_negotiated_price == Decimal('900.00')
    assert session.current_negotiated_unit_price == Decimal('900.00')
    print('[PASS] Round 7 reached: Single unit anchor firmly locked at Rs.900.00.')

    # Quantity 1
    r_q1 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', '1 unit')
    assert r_q1.validated_deal.quantity == 1
    assert r_q1.validated_deal.effective_unit_price == Decimal('900.00')
    assert r_q1.validated_deal.total_payable_amount == Decimal('900.00')
    print('[PASS] Qty 1: Rs.900.00/unit, Total Rs.900.00.')

    # Quantity 2 (No volume tier, must anchor on Rs.900, NEVER revert to Rs.1200)
    r_q2 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', 'What about 2 units?')
    assert r_q2.validated_deal.quantity == 2
    assert r_q2.validated_deal.effective_unit_price == Decimal('900.00'), f'Expected 900, got {r_q2.validated_deal.effective_unit_price}'
    assert r_q2.validated_deal.total_payable_amount == Decimal('1800.00'), f'Expected 1800, got {r_q2.validated_deal.total_payable_amount}'
    assert '1800.00' in r_q2.message or '1,800.00' in r_q2.message
    print('[PASS] Qty 2: Rs.900.00/unit, Total Rs.1800.00 (Anchored on negotiated Rs.900, did NOT revert to listed Rs.1200).')

    # Quantity 3 (No volume tier, must remain Rs.900 x 3 = Rs.2700)
    r_q3 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', 'How about 3?')
    assert r_q3.validated_deal.quantity == 3
    assert r_q3.validated_deal.effective_unit_price == Decimal('900.00')
    assert r_q3.validated_deal.total_payable_amount == Decimal('2700.00')
    print('[PASS] Qty 3: Rs.900.00/unit, Total Rs.2700.00.')

    # Quantity 4 (No volume tier, must remain Rs.900 x 4 = Rs.3600)
    r_q4 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', '4 pieces')
    assert r_q4.validated_deal.quantity == 4
    assert r_q4.validated_deal.effective_unit_price == Decimal('900.00')
    assert r_q4.validated_deal.total_payable_amount == Decimal('3600.00')
    print('[PASS] Qty 4: Rs.900.00/unit, Total Rs.3600.00.')

    # Quantity 5 (Qualifies for 10% volume discount on base 900: 900 x 5 = 4500 - 10% = 4050, Rs.810/unit)
    r_q5 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', 'Can you do 5 units?')
    assert r_q5.validated_deal.quantity == 5
    assert r_q5.validated_deal.effective_unit_price == Decimal('810.00')
    assert r_q5.validated_deal.total_payable_amount == Decimal('4050.00')
    assert '10%' in r_q5.message
    print('[PASS] Qty 5: Rs.810.00/unit, Total Rs.4050.00 (10% volume discount applied truthfully on Rs.900 base).')

    # ----------------------------------------------------
    # TEST 2: SELLER FLOOR PROTECTION & TRUTHFUL COMMUNICATON
    # ----------------------------------------------------
    print('\n--- TEST 2: Floor Clamping & Truthful Commercial Presentation ---')
    # For prod_004, reservation floor is Rs.800.00.
    # At quantity 10, volume tier discount is 18%.
    # 900 x (1 - 0.18) = 738.00, which breaches reservation price Rs.800!
    # Floor protection MUST clamp to Rs.800.00 (Total = Rs.8000.00).
    # Response must NOT claim '18% discount applied' and must NEVER mention reservation price or floor.
    r_q10 = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', 'What if I take 10 units?')
    assert r_q10.validated_deal.quantity == 10
    assert r_q10.validated_deal.effective_unit_price == Decimal('800.00'), f'Expected floor clamped 800, got {r_q10.validated_deal.effective_unit_price}'
    assert r_q10.validated_deal.total_payable_amount == Decimal('8000.00')
    assert '18% off' not in r_q10.message.lower()
    assert '18% discount' not in r_q10.message.lower()
    assert 'reservation' not in r_q10.message.lower()
    assert 'floor' not in r_q10.message.lower()
    assert 'clamped' not in r_q10.message.lower()
    print('[PASS] Floor protection clamped price to Rs.800.00 without false nominal discount claims and zero floor leakage.')

    # ----------------------------------------------------
    # TEST 3: SAFE FAILURE ON CORRUPTED/MISSING NEGOTIATION ANCHOR
    # ----------------------------------------------------
    print('\n--- TEST 3: Safe Failure on Missing Negotiated Anchor ---')
    policy_004 = db.get_seller_policy('prod_004')
    try:
        PolicyEngine.evaluate_offer(policy_004, buyer_offer=None, round_number=3, quantity=2, negotiated_unit_price=None)
        assert False, 'Should have failed safely on missing negotiated anchor in round > 1!'
    except ValueError as e:
        assert 'CORRUPTED NEGOTIATION STATE' in str(e) or 'Missing negotiated unit price anchor' in str(e)
        print('[PASS] Safe failure verified: Missing anchor in negotiated session raises ValueError (zero silent reset).')

    # ----------------------------------------------------
    # TEST 4: PAYMENT LIFECYCLE & HMAC-SHA256 SIGNATURE VERIFICATION
    # ----------------------------------------------------
    print('\n--- TEST 4: Payment Lifecycle & HMAC Signature State Machine ---')
    r_acc = AgentOrchestrator.process_user_message(sid_p4, 'prod_004', 'Ok done')
    assert r_acc.can_show_payment is True
    assert r_acc.validated_deal.effective_unit_price == Decimal('800.00') or r_acc.validated_deal.effective_unit_price == Decimal('810.00')

    # Step 4A: Create Order (VALIDATED_DEAL -> ORDER_CREATED)
    # Using the last validated deal for 10 units at 800.00
    rzp_req = RazorpayOrderRequest(
        session_id=sid_p4,
        product_id='prod_004',
        quantity=10,
        requested_unit_price=Decimal('800.00'),
        total_payable_amount=Decimal('8000.00'),
    )
    rzp_order = RazorpayService.create_order_safe(
        policy=policy_004,
        request=rzp_req,
        current_negotiated_unit_price=Decimal('900.00'),
        negotiation_round=7,
    )
    assert rzp_order.status == 'created'
    assert rzp_order.total_payable_amount == Decimal('8000.00')
    print(f'[PASS] State ORDER_CREATED: Razorpay order #{rzp_order.order_id} created.')

    # Step 4B: Cryptographic HMAC Signature Verification (ORDER_CREATED -> PAYMENT_CAPTURED -> ESCROW_RESERVED)
    valid_payment_id = 'pay_rzp_mock_test_12345'
    valid_sig = RazorpayService.generate_test_signature(rzp_order.order_id, valid_payment_id)

    # Test invalid signature rejection
    try:
        RazorpayService.verify_payment_safe(
            session_id=sid_p4,
            order_id=rzp_order.order_id,
            payment_id=valid_payment_id,
            signature='tampered_invalid_signature_hash',
            session=session_db.get_session(sid_p4),
        )
        assert False, 'Should have rejected invalid signature!'
    except ValueError as e:
        assert 'signature mismatch' in str(e).lower()
        print('[PASS] Tampered HMAC signature correctly rejected by cryptographic verification.')

    # Test valid signature acceptance
    verified_res = RazorpayService.verify_payment_safe(
        session_id=sid_p4,
        order_id=rzp_order.order_id,
        payment_id=valid_payment_id,
        signature=valid_sig,
        session=session_db.get_session(sid_p4),
    )
    assert verified_res.success is True
    assert verified_res.payment_status == 'PAYMENT_CAPTURED'
    assert verified_res.escrow_status == 'ESCROW_RESERVED'
    assert verified_res.effective_unit_price == Decimal('800.00')
    assert verified_res.total_payable_amount == Decimal('8000.00')
    print('[PASS] State PAYMENT_CAPTURED & ESCROW_RESERVED: Signature verified successfully.')

    # ----------------------------------------------------
    # TEST 5: EXPERIENCE STORE INTEGRATION
    # ----------------------------------------------------
    print('\n--- TEST 5: Experience Store Deal Trajectory Capture ---')
    from app.models import NegotiationExperience
    exp = NegotiationExperience(
        session_id=sid_p4,
        product_id='prod_004',
        starting_price=policy_004.listed_price,
        buyer_offers=[Decimal('800.00')],
        seller_counter_offers=[Decimal('900.00'), Decimal('800.00')],
        rounds=7,
        final_agreed_price=Decimal('800.00'),
        converted=True,
        quantity=10,
        seller_feedback='Verified payment captured in Authenticity Escrow.',
        successful_in_seller_view=True,
    )
    experience_store.save_experience(exp)

    retrieved_exp = experience_store.get_experience(sid_p4)
    assert retrieved_exp is not None
    assert retrieved_exp.session_id == sid_p4
    assert retrieved_exp.final_agreed_price == Decimal('800.00')
    assert retrieved_exp.converted is True
    assert retrieved_exp.quantity == 10
    print('[PASS] Experience Store successfully persisted and retrieved negotiation trajectory.')

    # ----------------------------------------------------
    # TEST 6: SECURITY & ISOLATION REGRESSION
    # ----------------------------------------------------
    print('\n--- TEST 6: Security & Isolation Regression ---')
    # Sub-floor tampering
    tampered_req = RazorpayOrderRequest(
        session_id=sid_p4,
        product_id='prod_004',
        quantity=1,
        requested_unit_price=Decimal('799.00'),
        total_payable_amount=Decimal('799.00'),
    )
    try:
        RazorpayService.create_order_safe(policy_004, tampered_req, current_negotiated_unit_price=Decimal('900.00'))
        assert False, 'Should have rejected sub-floor tampering!'
    except ValueError as e:
        assert 'PRE-CHECKOUT VALIDATION FAILURE' in str(e) or 'PRICE TAMPERING' in str(e)
        print('[PASS] Sub-floor price tampering rejected.')

    # Cross-product isolation: Switching to prod_001 in same session must reset state completely
    r_isolated = AgentOrchestrator.process_user_message(sid_p4, 'prod_001', 'Hello')
    sess_iso = session_db.get_session(sid_p4)
    assert sess_iso.product_id == 'prod_001'
    assert sess_iso.negotiation_round == 0
    assert sess_iso.single_unit_negotiated_price is None
    print('[PASS] Cross-product isolation verified: Switching product completely resets negotiation state.')

    print('\n[SUCCESS] ALL FINAL MVP HARDENING TESTS PASSED 100%!')


if __name__ == '__main__':
    test_final_mvp_hardening()
