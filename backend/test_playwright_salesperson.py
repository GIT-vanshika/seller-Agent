import sys
import time
from playwright.sync_api import sync_playwright

def run_browser_verification():
    print("==================================================")
    print("    PLAYWRIGHT SALESPERSON BROWSER VERIFICATION   ")
    print("==================================================")

    console_errors = []
    console_logs = []

    with sync_playwright() as p:
        # Launch Chrome browser
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Capture console messages
        def on_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", timeout=30000)
        page.wait_for_selector("input[type='text'], textarea", timeout=10000)

        # 1. Select prod_003 if selector exists
        print("Checking product selection...")
        prod_buttons = page.locator("button:has-text('Silk')")
        if prod_buttons.count() > 0:
            prod_buttons.first.click()
            time.sleep(1)

        input_field = page.locator("input[type='text'], textarea").first
        send_button = page.locator("button:has-text('Send'), button[type='submit']").first

        def send_message(text):
            print(f"Sending message: '{text}' ...")
            input_field.fill(text)
            send_button.click()
            time.sleep(2)
            # Wait for response to stabilize
            page.wait_for_timeout(1500)

        # 2. Turn 1: Lowball offer under 1900
        send_message("Can I get it under 1900?")
        t1_content = page.content()
        assert "2400" in t1_content or "2,400" in t1_content, "Round 1 counter Rs.2400 not found in page!"
        print("[PASS] Browser Turn 1 verified: Counter Rs.2400.00 displayed.")

        # 3. Turn 2: Ok 1800
        send_message("Ok 1800")
        t2_content = page.content()
        assert "2325" in t2_content or "2,325" in t2_content, "Round 2 counter Rs.2325 not found in page!"
        print("[PASS] Browser Turn 2 verified: Counter Rs.2325.00 displayed.")

        # 4. Turn 3: Ask for 2 pieces
        send_message("Can you do better if I take 2?")
        t3_content = page.content()
        assert "2125" in t3_content or "2,125" in t3_content, "2-piece price Rs.2125 not found in page!"
        print("[PASS] Browser Turn 3 verified: 2-piece price Rs.2125.00 displayed.")

        # 5. Turn 4: Accept with 'Ok done'
        send_message("Ok done")
        t4_content = page.content()
        assert "Deal confirmed" in t4_content or "locked" in t4_content or "Confirmed" in t4_content, "Deal confirmation not found!"
        print("[PASS] Browser Turn 4 verified: Active deal confirmed and locked.")

        # 6. Check console errors
        print("\nChecking console error logs...")
        print(f"Total console logs captured: {len(console_logs)}")
        print(f"Total console errors: {len(console_errors)}")
        if console_errors:
            print("Console Errors found:")
            for err in console_errors:
                print(f"  - {err}")
            assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
        else:
            print("[PASS] Browser console verified: 0 errors, 0 runtime exceptions.")

        browser.close()

    print("\n[SUCCESS] PLAYWRIGHT BROWSER VERIFICATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_browser_verification()

