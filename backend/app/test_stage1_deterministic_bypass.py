from decimal import Decimal
from unittest.mock import patch
from app.intent_classifier import IntentClassifier
from app.orchestrator import AgentOrchestrator
from app.gemini_intent_service import GeminiIntentService
from app.data_loader import db


def test_stage1_deterministic_bypass():
    print("==================================================================")
    print("   TESTING DETERMINISTIC STAGE 1 GEMINI BYPASS & ROUTING        ")
    print("==================================================================")

    # 1. Test is_unambiguous_intent directly
    test_cases_unambiguous = [
        # (text, in_negotiation, expected_primary_intent)
        ("Can you give me some discount?", False, "price_negotiation"),
        ("Thoda kam karo please", False, "price_negotiation"),
        ("What's your best price?", False, "price_negotiation"),
        ("I'll take it", True, "purchase_intent"),
        ("Ok done", True, "purchase_intent"),
        ("Agreed, let's do it", True, "purchase_intent"),
        ("How do I pay?", True, "purchase_intent"),
        ("Where can I pay?", False, "purchase_intent"),
        ("I'll think about it", True, "clarification"),
        ("Let me think about it", False, "clarification"),
        ("Will think and let you know", True, "clarification"),
        ("What if I take 5?", False, "quantity_pricing_query"),
        ("For 3 units what price?", False, "quantity_pricing_query"),
        ("How much for 5 pieces?", False, "quantity_pricing_query"),
        ("Can you do 1800?", False, "price_negotiation"),
        ("1750 final", True, "price_negotiation"),
        ("Hi", False, "general_conversation"),
        ("Hello there", False, "general_conversation"),
        ("Namaste", False, "general_conversation"),
        ("Can I see real photo?", False, "product_question"),
        ("Show unedited video", False, "product_question"),
        ("Is this pure silk?", False, "product_question"),
    ]

    for text, in_neg, exp_intent in test_cases_unambiguous:
        is_unambig, decision = IntentClassifier.is_unambiguous_intent(text, in_negotiation=in_neg)
        assert is_unambig is True, f"Expected '{text}' to be recognized as unambiguous"
        assert decision is not None
        assert decision.primary_intent == exp_intent, f"For '{text}', expected {exp_intent}, got {decision.primary_intent}"
        print(f"  [PASS] '{text}' -> unambiguous {decision.primary_intent} (Bypasses Stage 1 Gemini)")

    # 2. Test ambiguous messages that SHOULD route to Stage 1 Gemini
    test_cases_ambiguous = [
        "It is nice but I am just exploring options",
        "My cousin mentioned something about this yesterday",
        "Interesting colors maybe next month",
    ]

    for text in test_cases_ambiguous:
        is_unambig, decision = IntentClassifier.is_unambiguous_intent(text, in_negotiation=False)
        assert is_unambig is False, f"Expected '{text}' to be marked ambiguous"
        assert decision is None
        print(f"  [PASS] Ambiguous message '{text}' -> routes to Stage 1 Gemini")

    # 3. Verify in Orchestrator pipeline: Stage 1 Gemini is NOT called for unambiguous turns
    stage1_call_count = 0
    orig_understand = GeminiIntentService.understand_buyer_intent

    def mock_understand(*args, **kwargs):
        nonlocal stage1_call_count
        stage1_call_count += 1
        return orig_understand(*args, **kwargs)

    with patch.object(GeminiIntentService, "understand_buyer_intent", side_effect=mock_understand):
        sid = "sess_test_quota_bypass"
        pid = "prod_003"

        # Turn 1: Greeting -> unambiguous, 0 Stage 1 calls
        stage1_call_count = 0
        AgentOrchestrator.process_user_message(sid, pid, "Hello")
        assert stage1_call_count == 0, f"Expected 0 Stage 1 calls for greeting, got {stage1_call_count}"
        print("  [PASS] Turn 1 ('Hello'): Stage 1 Gemini calls = 0 (Bypassed!)")

        # Turn 2: Offer -> unambiguous, 0 Stage 1 calls
        stage1_call_count = 0
        AgentOrchestrator.process_user_message(sid, pid, "Can you do 1800?")
        assert stage1_call_count == 0, f"Expected 0 Stage 1 calls for numeric offer, got {stage1_call_count}"
        print("  [PASS] Turn 2 ('Can you do 1800?'): Stage 1 Gemini calls = 0 (Bypassed!)")

        # Turn 3: Deliberation -> unambiguous, 0 Stage 1 calls
        stage1_call_count = 0
        res_delib = AgentOrchestrator.process_user_message(sid, pid, "I'll think about it")
        assert stage1_call_count == 0, f"Expected 0 Stage 1 calls for deliberation, got {stage1_call_count}"
        assert res_delib.can_show_payment is False
        assert res_delib.deal_status == "negotiating"
        print("  [PASS] Turn 3 ('I'll think about it'): Stage 1 Gemini calls = 0, can_show_payment=False")

        # Turn 4: Acceptance -> unambiguous, 0 Stage 1 calls
        stage1_call_count = 0
        res_acc = AgentOrchestrator.process_user_message(sid, pid, "I'll take it")
        assert stage1_call_count == 0, f"Expected 0 Stage 1 calls for acceptance, got {stage1_call_count}"
        assert res_acc.can_show_payment is True
        assert res_acc.deal_status == "agreed"
        print("  [PASS] Turn 4 ('I'll take it'): Stage 1 Gemini calls = 0, can_show_payment=True")

    print("\n==================================================================")
    print("   [SUCCESS] ALL STAGE 1 DETERMINISTIC BYPASS TESTS PASSED 100%    ")
    print("==================================================================")


if __name__ == "__main__":
    test_stage1_deterministic_bypass()
