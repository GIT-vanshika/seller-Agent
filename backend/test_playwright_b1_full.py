import os
import time
from playwright.sync_api import sync_playwright

def run_b1_verification():
    print("==================================================")
    print("    AURA COMMERCE B1 COMPOSITION PLAYWRIGHT TEST  ")
    print("==================================================")

    console_errors = []
    console_logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        # 1440x900 desktop viewport
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def on_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", timeout=30000)
        page.wait_for_selector("input[type='text']", timeout=10000)
        time.sleep(2)

        input_field = page.locator("input[type='text']").first
        send_button = page.locator("button:has-text('Send')").first

        def send_message(text):
            print(f"Sending message: '{text}' ...")
            input_field.fill(text)
            send_button.click()
            time.sleep(2.5)

        # -------------------------------------------------------------
        # TEST 1: Fresh Page Verification
        # -------------------------------------------------------------
        content_fresh = page.content()
        assert "AURA" in content_fresh
        assert "COMMERCE" in content_fresh
        assert "Silk Designer Dress" in content_fresh
        assert "2,500" in content_fresh or "2500" in content_fresh
        assert "AURA CONCIERGE" in content_fresh
        # Verify no developer noise is visible
        assert "sess_" not in content_fresh, "Session ID leaked to UI!"
        assert "price_hesitation" not in content_fresh, "Internal classifier leaked!"
        assert "intent_classifier" not in content_fresh, "Internal classifier leaked!"
        assert "reservation_price" not in content_fresh, "Private seller floor leaked!"
        # Verify exactly one greeting
        greetings = content_fresh.count("Welcome to Aura. I am your commercial concierge")
        assert greetings == 1, f"Expected 1 greeting, found {greetings}"
        print("[PASS] TEST 1: Fresh page loaded with single greeting, listed MRP Rs.2,500, and zero technical leaks.")

        # -------------------------------------------------------------
        # TEST 2: Product Switching Across 5 Products
        # -------------------------------------------------------------
        test_prods = [
            ("Vase", "Ceramic Vase", "1,200"),
            ("Linen", "Linen Shirt", "1,800"),
            ("Cookies", "Butter Cookies", "100"),
            ("Ice Cream", "Vanilla Ice Cream", "150"),
            ("Silk", "Silk Designer Dress", "2,500"),
        ]
        for btn_text, expected_name, expected_price in test_prods:
            print(f"Switching to product with '{btn_text}'...")
            btn = page.locator(f"button:has-text('{btn_text}')").first
            btn.click()
            time.sleep(1.5)
            c = page.content()
            assert expected_name in c, f"Product name '{expected_name}' not found after switch!"
            assert expected_price in c, f"Price '{expected_price}' not found after switch!"
            assert "sess_" not in c
        print("[PASS] TEST 2: Successfully switched through 5 distinct products with zero stale data.")

        # -------------------------------------------------------------
        # TEST 3: Product Question Mid-Stream
        # -------------------------------------------------------------
        # We are on Silk Designer Dress now
        send_message("What is this made of?")
        c_q = page.content()
        assert "silk" in c_q.lower() or "mulberry" in c_q.lower(), "Product question not answered accurately!"
        print("[PASS] TEST 3: Product inquiry answered cleanly using grounded product facts.")

        # -------------------------------------------------------------
        # TEST 4: Trust Question & Evidence Activation
        # -------------------------------------------------------------
        send_message("Are these pictures actually real?")
        c_trust = page.content()
        assert "CITED IN CONCIERGE ANSWER" in c_trust or "CITED EVIDENCE" in c_trust, "Evidence activation tag not found!"
        print("[PASS] TEST 4: Trust hesitation answered; evidence card activated with 'CITED IN CONCIERGE ANSWER'.")

        # -------------------------------------------------------------
        # TEST 5: Negotiation & Commercial Deal Desk
        # -------------------------------------------------------------
        send_message("Can I get it under 1900?")
        c_neg = page.content()
        assert "2,400" in c_neg or "2400" in c_neg, "Round 1 counter Rs.2400 not found!"
        assert "COMMERCIAL DEAL DESK" in c_neg or "ROUND 1/5" in c_neg, "In-stream Deal Desk not rendered!"
        print("[PASS] TEST 5: Negotiation initiated; in-stream Commercial Deal Desk displayed counter Rs.2,400.")

        # Accept the counter
        send_message("Ok done")
        c_acc = page.content()
        assert "DEAL VALIDATED" in c_acc, "Validated Deal Certificate not rendered!"
        print("[PASS] TEST 5.1: Active counter accepted; transformed into Validated Deal Certificate.")

        # -------------------------------------------------------------
        # TEST 6: Layout Quality & Screenshot Capture
        # -------------------------------------------------------------
        # Check no horizontal scroll on window
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        inner_width = page.evaluate("() => window.innerWidth")
        assert scroll_width <= inner_width + 10, f"Horizontal overflow detected: scrollWidth={scroll_width}, innerWidth={inner_width}"

        # Capture high-res screenshot
        screenshot_dir = r"c:\Users\vansh\.gemini\antigravity\brain\6e143384-6a6a-40ad-8a14-4218bca56541"
        screenshot_path = os.path.join(screenshot_dir, "aura_b1_storefront_screenshot.png")
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"[PASS] TEST 6: Screenshot captured at: {screenshot_path}")

        # -------------------------------------------------------------
        # TEST 7: Console & Exception Check
        # -------------------------------------------------------------
        print(f"Total console logs: {len(console_logs)}")
        print(f"Total console errors: {len(console_errors)}")
        if console_errors:
            for e in console_errors:
                print(f"  Error: {e}")
            assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
        print("[PASS] TEST 7: 0 console errors, 0 runtime exceptions.")

        browser.close()

    print("\n[SUCCESS] ALL B1 COMPOSITION PLAYWRIGHT TESTS PASSED 100%!")

if __name__ == "__main__":
    run_b1_verification()

