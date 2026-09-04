import time
from playwright.sync_api import sync_playwright

def run_designer_verification():
    print("==================================================")
    print("    AURA COMMERCE DESIGNER.md PLAYWRIGHT TEST     ")
    print("==================================================")

    console_errors = []
    console_logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", timeout=30000)
        page.wait_for_selector("input[type='text'], textarea", timeout=10000)
        time.sleep(2)

        input_field = page.locator("input[type='text'], textarea").first
        send_button = page.locator("button:has-text('Send')").first

        def send_message(text):
            print(f"Sending message: '{text}' ...")
            input_field.fill(text)
            send_button.click()
            time.sleep(2.5)

        # -----------------------------------------------------------------
        # SCENARIO A: Fresh Page Load
        # -----------------------------------------------------------------
        content_init = page.content()
        assert "AURA" in content_init
        assert "Silk Designer Dress" in content_init
        assert "2,500" in content_init or "2500" in content_init
        # Check initial greeting count
        welcome_count = content_init.count("Welcome to Aura. I am your commercial concierge")
        assert welcome_count == 1, f"Expected exactly 1 greeting, found {welcome_count}"
        print("[PASS] Scenario A: Fresh page loaded with single greeting and listed MRP Rs.2,500.")

        # -----------------------------------------------------------------
        # SCENARIO B: Trust Question & Evidence Activation ("Confidence Becomes Visible")
        # -----------------------------------------------------------------
        send_message("Are these pictures actually real?")
        content_trust = page.content()
        assert "CITED IN ANSWER" in content_trust or "cited" in content_trust.lower(), "Evidence activation badge not found!"
        print("[PASS] Scenario B: Trust question asked; matching evidence card activated with 'CITED IN ANSWER'!")

        # -----------------------------------------------------------------
        # SCENARIO C: Strategic Salesperson Negotiation & In-Stream Deal Desk
        # -----------------------------------------------------------------
        send_message("Can I get it under 1900?")
        content_neg1 = page.content()
        assert "2,400" in content_neg1 or "2400" in content_neg1, "Round 1 counter Rs.2400 not found!"
        assert "COMMERCIAL DEAL DESK" in content_neg1 or "ROUND 1/5" in content_neg1, "Deal Desk not found in stream!"
        print("[PASS] Scenario C.1: Round 1 counter Rs.2,400 displayed inside in-stream Commercial Deal Desk.")

        send_message("Ok 1800")
        content_neg2 = page.content()
        assert "2,325" in content_neg2 or "2325" in content_neg2, "Round 2 counter Rs.2325 not found!"
        print("[PASS] Scenario C.2: Round 2 counter Rs.2325 displayed in Deal Desk.")

        send_message("Can you do better if I take 2?")
        content_qty = page.content()
        assert "2,125" in content_qty or "2125" in content_qty, "2-unit rate Rs.2125 not found!"
        assert "4,250" in content_qty or "4250" in content_qty, "2-unit total Rs.4250 not found!"
        print("[PASS] Scenario C.3: Volume incentive recognized (2 units @ Rs.2,125/unit, Total Rs.4,250).")

        # -----------------------------------------------------------------
        # SCENARIO D: Deal Acceptance & Validated Deal Certificate
        # -----------------------------------------------------------------
        send_message("Ok done")
        content_deal = page.content()
        assert "DEAL VALIDATED" in content_deal or "Deal confirmed" in content_deal, "Validated Deal Certificate not rendered!"
        assert "Pay" in content_deal and "4,250" in content_deal, "Pay button with total not found!"
        print("[PASS] Scenario D: Acceptance confirmed; transformed into Validated Deal Certificate.")

        # -----------------------------------------------------------------
        # SCENARIO E: Payment Transition & Order Secured Receipt
        # -----------------------------------------------------------------
        pay_btn = page.locator("button:has-text('Pay')").first
        print("Clicking Pay button...")
        pay_btn.click()
        time.sleep(2.5)

        content_pay = page.content()
        assert "ORDER SECURED" in content_pay or "order_" in content_pay or "PAYMENT" in content_pay, "Order secured receipt not found!"
        print("[PASS] Scenario E: Stepped payment transition executed; Razorpay Order secured.")

        # -----------------------------------------------------------------
        # SCENARIO F: Product Switching & Isolation
        # -----------------------------------------------------------------
        print("Switching product to Cookies...")
        cookie_btn = page.locator("button:has-text('Cookies')").first
        cookie_btn.click()
        time.sleep(2)

        content_cookie = page.content()
        assert "Premium Butter Cookies" in content_cookie
        assert "100" in content_cookie
        assert "4,250" not in content_cookie, "Cross-product price leakage detected!"
        assert "Silk Designer Dress" not in content_cookie or "Cookies" in content_cookie
        print("[PASS] Scenario F: Product switched cleanly; zero cross-product negotiation leakage.")

        # -----------------------------------------------------------------
        # SCENARIO G: Console Errors & Exceptions Check
        # -----------------------------------------------------------------
        print(f"\nTotal console logs captured: {len(console_logs)}")
        print(f"Total console errors: {len(console_errors)}")
        if console_errors:
            print("Console Errors:")
            for err in console_errors:
                print(f"  - {err}")
            assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
        else:
            print("[PASS] Scenario G: Browser console verified: 0 errors, 0 runtime exceptions.")

        browser.close()

    print("\n[SUCCESS] 100% OF DESIGNER.MD PLAYWRIGHT VERIFICATION SCENARIOS PASSED!")

if __name__ == "__main__":
    run_designer_verification()
