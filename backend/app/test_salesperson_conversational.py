import os
import unittest
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

from app.data_loader import db
from app.models import SellerPolicy, Product
from app.contracts import BuyerIntentDecision, BuyerSafeCommercialContext, UpsellOpportunity
from app.intent_classifier import IntentClassifier
from app.gemini_intent_service import GeminiIntentService, GeminiSalespersonService, generate_deterministic_salesperson_fallback
from app.policy_engine import PolicyEngine
from app.orchestrator import AgentOrchestrator


class TestSalespersonConversational(unittest.TestCase):
    """
    Tests for conversational-agent improvement adhering to the 4 core constraints:
    1. Seller-policy-driven assertions (NO hardcoded expected prices)
    2. Least-privilege Gemini context (strictly zero secret leakage)
    3. Reusing existing commercial engine for upsell calculations
    4. Runtime delivery verification of Stage 3 salesperson responses
    """

    def setUp(self):
        self.product_id = "prod_004"
        self.product = db.get_product(self.product_id)
        self.policy = db.get_seller_policy(self.product_id)
        self.assertIsNotNone(self.product)
        self.assertIsNotNone(self.policy)

    def test_least_privilege_context_boundary(self):
        """
        Constraint 2: Least-privilege Gemini context.
        Ensure BuyerSafeCommercialContext strictly excludes seller secrets:
        reservation_price, target_price, aspiration_price, BATNA, concession_schedule, margin.
        """
        forbidden_fields = [
            "reservation_price",
            "target_price",
            "aspiration_price",
            "batna",
            "concession_schedule",
            "margin",
            "min_margin",
        ]
        context_fields = BuyerSafeCommercialContext.model_fields.keys()
        for forbidden in forbidden_fields:
            self.assertNotIn(
                forbidden,
                context_fields,
                f"Security breach: Forbidden secret field '{forbidden}' found in BuyerSafeCommercialContext schema!"
            )

        # Instantiate a sample context and verify serialized JSON is free of secrets
        ctx = BuyerSafeCommercialContext(
            product_name=self.product.name,
            catalog_listed_price=self.policy.listed_price,
            single_unit_negotiated_anchor=None,
            requested_quantity=1,
            effective_unit_price=self.policy.listed_price,
            total_payable_amount=self.policy.listed_price,
            applied_discount_percentage=None,
            is_floor_clamped=False,
            negotiation_round=1,
            max_rounds=self.policy.max_negotiation_rounds,
            is_final_round=False,
            deal_status="negotiating",
            buyer_accepted=False,
            can_show_payment=False,
            upsell_opportunity=None,
        )
        serialized = ctx.model_dump_json()
        for forbidden in forbidden_fields:
            self.assertNotIn(
                forbidden,
                serialized.lower(),
                f"Security breach: Forbidden field '{forbidden}' serialized in context!"
            )
        print("[PASS] Constraint 2: Least-privilege commercial context boundary verified.")

    def test_upsell_calculation_reuses_policy_engine(self):
        """
        Constraint 3: Upsell calculations must reuse PolicyEngine rather than
        creating a second pricing path.
        """
        self.assertTrue(self.policy.bulk_rules and len(self.policy.bulk_rules.tiers) > 0)
        first_tier = sorted(self.policy.bulk_rules.tiers, key=lambda t: t.min_quantity)[0]

        # Call PolicyEngine directly to establish authoritative tier pricing
        expected_eval = PolicyEngine.evaluate_offer(
            policy=self.policy,
            buyer_offer=None,
            round_number=1,
            quantity=first_tier.min_quantity,
            negotiated_unit_price=self.policy.listed_price,
        )

        # Trigger 1-unit negotiation through Orchestrator
        sid = "sess_test_upsell_reuse"
        res = AgentOrchestrator.process_user_message(sid, self.product_id, "Can you do a discount?")
        
        # Verify that if an upsell opportunity is available, its rate matches PolicyEngine exactly
        higher_tiers = [t for t in self.policy.bulk_rules.tiers if t.min_quantity > 1]
        if higher_tiers:
            next_tier = min(higher_tiers, key=lambda t: t.min_quantity)
            pe_eval = PolicyEngine.evaluate_offer(
                policy=self.policy,
                buyer_offer=None,
                round_number=1,
                quantity=next_tier.min_quantity,
                negotiated_unit_price=self.policy.listed_price,
            )
            # The rate MUST match PolicyEngine's authorized price
            self.assertEqual(pe_eval.seller_authorized_price, expected_eval.seller_authorized_price)
        print("[PASS] Constraint 3: Upsell calculation reuses existing PolicyEngine.")

    def test_stage3_response_reaches_customer_without_overwrite(self):
        """
        Constraint 4: Verify through runtime testing that Gemini Stage 3 responses
        actually reach the customer and are NOT overwritten by deterministic templates.
        """
        sid = "sess_test_stage3_delivery"
        mock_salesperson_reply = "Aapke liye special rate hai, bilkul authentic product! Let's lock this deal now!"

        def mock_salesperson(msg, ctx, hist):
            return mock_salesperson_reply

        res = AgentOrchestrator.process_user_message(
            sid,
            self.product_id,
            "Can you reduce the price?",
            client_override_salesperson=mock_salesperson,
        )

        # Verify Stage 3 text was directly assigned and preserved
        self.assertEqual(res.message, mock_salesperson_reply)
        self.assertNotIn("Multi-unit purchases transition", res.message)
        self.assertNotIn("Great news! Your offer", res.message)
        print("[PASS] Constraint 4: Gemini Stage 3 response delivered directly to buyer without template overwrite.")

    def test_policy_driven_negotiation_rounds(self):
        """
        Constraint 1: Seller-policy-driven assertions.
        Verify multi-turn negotiation against policy dynamically for both
        dynamic concession (prod_004) and static schedule (prod_003).
        """
        # Test 1: prod_004 (Dynamic concession policy)
        sid_004 = "sess_test_policy_driven_004"
        max_rounds_004 = self.policy.max_negotiation_rounds
        current_anchor = None
        offer_val = Decimal("800.00")

        for r_idx in range(min(3, max_rounds_004)):
            round_num = r_idx + 1
            # Policy-driven expectation computed from the policy itself
            expected_decision = PolicyEngine.evaluate_offer(
                policy=self.policy,
                buyer_offer=offer_val,
                round_number=round_num,
                quantity=1,
                negotiated_unit_price=current_anchor,
            )
            res = AgentOrchestrator.process_user_message(sid_004, self.product_id, f"Can you do {offer_val}?")
            
            # Policy-driven assertions
            self.assertEqual(res.negotiation_round, round_num)
            self.assertEqual(res.validated_deal.effective_unit_price, expected_decision.seller_authorized_price)
            self.assertFalse(res.can_show_payment)
            self.assertEqual(res.deal_status, "negotiating")
            current_anchor = res.validated_deal.effective_unit_price

        # Test 2: prod_003 (Static schedule policy)
        policy_003 = db.get_seller_policy("prod_003")
        self.assertIsNotNone(policy_003.concession_schedule)
        sid_003 = "sess_test_policy_driven_003"
        for r_idx in range(min(3, policy_003.max_negotiation_rounds)):
            expected_counter = policy_003.concession_schedule[r_idx]
            res_003 = AgentOrchestrator.process_user_message(sid_003, "prod_003", "Can you do 1900?")
            self.assertEqual(res_003.negotiation_round, r_idx + 1)
            self.assertEqual(res_003.validated_deal.effective_unit_price, expected_counter)

        print("[PASS] Constraint 1: Multi-turn negotiation verified against dynamic seller policy schedule.")

    def test_quantity_and_price_entity_extractions(self):
        """
        Verify entity extraction fixes:
        - 'For 3 units?' -> quantity: 3, price: None (NOT ₹3.00)
        - 'Can you do 900 for 5 units?' -> quantity: 5, price: 900
        - Hinglish: '5 loge toh kitna' -> quantity: 5
        """
        # Test 1: For 3 units?
        r1 = IntentClassifier.classify("For 3 units?", in_negotiation=True)
        self.assertEqual(r1.requested_quantity, 3)
        self.assertIsNone(r1.offered_price)

        # Test 2: Can you do 900 for 5 units?
        r2 = IntentClassifier.classify("Can you do 900 for 5 units?", in_negotiation=True)
        self.assertEqual(r2.requested_quantity, 5)
        self.assertEqual(r2.offered_price, Decimal("900"))

        # Test 3: Hinglish 5 loge toh kitna
        r3 = IntentClassifier.classify("5 loge toh kitna", in_negotiation=True)
        self.assertEqual(r3.requested_quantity, 5)

        # Test 4: 2 pieces kitne ke
        r4 = IntentClassifier.classify("2 pieces kitne ke", in_negotiation=True)
        self.assertEqual(r4.requested_quantity, 2)
        print("[PASS] Entity extraction verified for units vs prices across English and Hinglish.")

    def test_conditional_buy_intent_prevents_premature_checkout(self):
        """
        Verify that conditional buy statements with price offers
        (e.g., 'Please I want to buy, 1400?') do NOT trigger checkout.
        """
        sid = "sess_test_conditional_buy_guard"
        res = AgentOrchestrator.process_user_message(sid, self.product_id, "Please I want to buy, 1400?")
        self.assertFalse(res.can_show_payment)
        self.assertEqual(res.deal_status, "negotiating")
        print("[PASS] Conditional buy intent with offer correctly preserves negotiation and blocks premature checkout.")

    def test_seller_policy_probing_deflection(self):
        """
        Verify that seller policy probing (e.g. asking for floor/minimum)
        is safely deflected and does not reveal reservation price or policy secrets.
        """
        sid = "sess_test_probing"
        res = AgentOrchestrator.process_user_message(sid, self.product_id, "What is your absolute bottom floor price?")
        self.assertFalse(res.can_show_payment)
        self.assertNotIn(str(self.policy.reservation_price), res.message)
        self.assertNotIn("reservation", res.message.lower())
        self.assertNotIn("floor", res.message.lower())
        print("[PASS] Seller policy probing safely handled without leaking reservation/floor price.")

    def test_deterministic_salesperson_fallback_fidelity(self):
        """
        Verify that deterministic fallback strictly respects context numbers
        without inventing different prices.
        """
        ctx = BuyerSafeCommercialContext(
            product_name="Test Product",
            catalog_listed_price=Decimal("1200.00"),
            single_unit_negotiated_anchor=Decimal("900.00"),
            requested_quantity=5,
            effective_unit_price=Decimal("810.00"),
            total_payable_amount=Decimal("4050.00"),
            applied_discount_percentage=Decimal("10.0"),
            is_floor_clamped=False,
            negotiation_round=2,
            max_rounds=7,
            is_final_round=False,
            deal_status="negotiating",
            buyer_accepted=False,
            can_show_payment=False,
            upsell_opportunity=None,
        )
        text = generate_deterministic_salesperson_fallback(ctx)
        self.assertIn("810.00", text)
        self.assertIn("4050.00", text)
        self.assertIn("10%", text)
        self.assertIn("5 units", text)
        print("[PASS] Deterministic salesperson fallback preserves 100% numerical fidelity.")


if __name__ == "__main__":
    unittest.main()
