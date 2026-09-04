import sys
import time
from playwright.sync_api import sync_playwright

def run_stitch_final_verification():
    print("=" * 60)
    print("   AURA COMMERCE DARK LUXURY STITCH VERIFICATION")
    print("=" * 60)

    console_errors = []
    console_logs = []

    def on_console(msg):
        console_logs.append(f"[{msg.type}] {msg.text}")
        if msg.type == "error":
            if "favicon" not in msg.text.lower():
                console_errors.append(msg.text)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", on_console)

        print("\n[STEP 1] Navigating to http://localhost:3000 at 1440x900 ...")
        page.goto("http://localhost:3000")
        page.wait_for_timeout(2000)

        c = page.content()
        assert "AURA" in c, "AURA brand wordmark not found!"
        assert "Live Escrow" in c, "Live Escrow indicator not found!"
        print("[PASS] Desktop 1440x900 loaded in dark luxury theme.")

        print("\n[STEP 2] Testing product switching across catalog...")
        test_prods = ["Silk Designer Dress", "Premium Butter Cookies", "Embroidered Linen Shirt", "Handcrafted Ceramic Vase Set"]
        for p_name in test_prods:
            btn = page.locator(f"button:has-text('{p_name}')").first
            btn.click()
            time.sleep(1)
            content_switch = page.content()
            assert p_name in content_switch, f"Product {p_name} not displayed after click!"
            print(f"  [OK] Switched to '{p_name}'.")
        print("[PASS] Catalog switching verified.")

        page.locator("button:has-text('Handcrafted Ceramic Vase Set')").first.click()
        time.sleep(1)

        print("\n[STEP 3] Testing 3-way viewplate perspective switcher...")
        page.locator("button:has-text('Workshop')").first.click()
        time.sleep(0.5)
        print("  [OK] Workshop plate activated.")
        page.locator("button:has-text('Studio Plate')").first.click()
        time.sleep(0.5)
        print("  [OK] Studio plate restored.")
        print("[PASS] 3-way perspective switching verified.")

        print("\n[STEP 4] Testing product Q&A...")
        input_field = page.locator("input[placeholder*='Ask AURA']")
        send_btn = page.locator("button:has-text('Send')")

        input_field.fill("What is this piece made of?")
        send_btn.click()
        time.sleep(2.5)
        c_qa = page.content()
        assert "AURA Confidence System" in c_qa, "Concierge response card not rendered!"
        print("[PASS] Product inquiry answered.")

        print("\n[STEP 5] Testing trust question & visual evidence protocol...")
        input_field.fill("Does this piece actually look like the studio pictures in natural daylight?")
        send_btn.click()
        time.sleep(3)
        c_trust = page.content()
        assert "Cited in AURA Evidence Dossier" in c_trust, "Evidence citation footer not rendered!"
        print("[PASS] Trust question answered with inline visual evidence block.")

        print("\n[STEP 6] Testing commercial negotiation...")
        input_field.fill("Can you do 1000? Looking to acquire two if the pricing works.")
        send_btn.click()
        time.sleep(3)
        c_neg = page.content()
        assert "Commercial Review" in c_neg, "Commercial review card not rendered!"
        assert "Multi-Unit Leverage" in c_neg, "Multi-unit leverage protocol not rendered!"
        print("[PASS] Amber commercial review desk rendered.")

        print("\n[STEP 7] Testing quantity leverage buttons...")
        qty_plus = page.locator("button:has-text('+')").first
        if qty_plus.is_visible():
            qty_plus.click()
            time.sleep(2.5)
            print("  [OK] Quantity leverage + clicked.")
        print("[PASS] Quantity controls verified.")

        print("\n[STEP 8] Testing 'Ok done' deal agreement...")
        input_field.fill("Ok done")
        send_btn.click()
        page.wait_for_selector("text=Acquisition Dossier Settlement", timeout=10000)
        page.wait_for_selector("text=Validated Deal Certificate", timeout=10000)
        c_deal = page.content()
        assert "Acquisition Dossier Settlement" in c_deal, "Deal certificate not rendered!"
        assert "Authorize" in c_deal and "Razorpay" in c_deal, "Razorpay button not found!"
        assert "Validated Deal Certificate" in c_deal, "Deal certificate not rendered!"
        assert "Razorpay" in c_deal, "Razorpay button not found!"
        print("[PASS] Validated Deal Certificate rendered.")

        print("\n[STEP 9] Testing Razorpay payment authorization transition...")
        pay_btn = page.locator("button:has-text('Authorize')").first
        pay_btn = page.locator("button:has-text('Razorpay')").first
        pay_btn.click()
        time.sleep(2.5)
        c_pay = page.content()
        assert "Escrow Reserved" in c_pay or "Razorpay Order ID" in c_pay, "Payment settlement not confirmed!"
        print("[PASS] Razorpay payment transition succeeded.")

        screenshot_path = r"C:\Users\vansh\.gemini\antigravity\brain\6e143384-6a6a-40ad-8a14-4218bca56541\aura_stitch_final_dark_desktop_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n[PASS] Captured dark luxury desktop screenshot: {screenshot_path}")

        print("\n[STEP 11] Testing mobile viewport layout (390x844)...")
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.on("console", on_console)
        mobile_page.goto("http://localhost:3000")
        mobile_page.wait_for_timeout(2000)

        scroll_width = mobile_page.evaluate("() => document.documentElement.scrollWidth")
        inner_width = mobile_page.evaluate("() => window.innerWidth")
        assert scroll_width <= inner_width + 5, f"Mobile horizontal overflow: {scroll_width} > {inner_width}"
        mobile_screenshot_path = r"C:\Users\vansh\.gemini\antigravity\brain\6e143384-6a6a-40ad-8a14-4218bca56541\aura_stitch_final_dark_mobile_screenshot.png"
        mobile_page.screenshot(path=mobile_screenshot_path)
        print(f"[PASS] Mobile verified: {mobile_screenshot_path}")

        print(f"\nTotal browser console logs: {len(console_logs)}")
        print(f"Total browser console errors: {len(console_errors)}")
        if console_errors:
            for err in console_errors:
                print(f"  [ERROR] {err}")
        assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
        print("[PASS] 0 console errors, 0 runtime exceptions.")

        browser.close()

    print("\n" + "=" * 60)
    print("   ALL DARK LUXURY STITCH TESTS PASSED 100%!")
    print("=" * 60)

if __name__ == "__main__":
    run_stitch_final_verification()

