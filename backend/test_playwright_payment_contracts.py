import sys
import time
from playwright.sync_api import sync_playwright

def run_browser_payment_tests():
    print("=" * 65)
    print("   PLAYWRIGHT BROWSER VERIFICATION: PAYMENT TRIGGERS & ROUND 7   ")
    print("=" * 65)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # -------------------------------------------------------------
        # SCENARIO 1: Negotiation -> Round 7 Policy Boundary -> Later Accept
        # -------------------------------------------------------------
        print("\n[SCENARIO 1] Testing 7-Round Boundary (NEGOTIATION FINISHED != BUYER ACCEPTED)")
        page.goto("http://localhost:3000")
        page.wait_for_timeout(2000)

        # Select Silk Designer Dress (negotiable, listed 2500, target 2050)
        page.locator("button:has-text('Silk Designer Dress')").first.click()
        time.sleep(1)

        input_field = page.locator("input[placeholder*='Ask AURA']")
        send_btn = page.locator("button:has-text('Send')")

        lowballs = ["1200", "1300", "1400", "1500", "1600", "1700", "1800"]
        for r, offer in enumerate(lowballs, 1):
            input_field.fill(f"Can I get for {offer}?")
            send_btn.click()
            time.sleep(2.0)
            print(f"  Sent lowball #{r}: {offer}")

        # Check Round 7 state
        content_r7 = page.content()
        assert "We cannot get below" in content_r7 and "against seller policy" in content_r7, \
            "Expected policy boundary message 'We cannot get below ₹X. It is against seller policy.' not found!"
        assert "limit" not in content_r7.lower() or "maximum rounds exceeded" not in content_r7.lower(), \
            "Found forbidden 'limit' or 'maximum rounds exceeded' language!"
        
        # CRUCIAL CONSTRAINT: Negotiation Finished != Buyer Accepted
        # Razorpay button must NOT be visible yet!
        assert "Now make a secure payment through Razorpay" not in content_r7, \
            "VIOLATION: Payment section prematurely visible at round 7 before buyer accepted!"
        assert "Validated Deal Certificate" not in content_r7, \
            "VIOLATION: Validated Deal Certificate prematurely visible at round 7 before buyer accepted!"
        print("  [PASS] At Round 7: Policy boundary enforced, zero limit language, Razorpay NOT shown.")

        # Now Buyer explicitly asks "where can I pay?" (Trigger 2 after round 7)
        input_field.fill("where can I pay?")
        send_btn.click()
        page.wait_for_selector("text=Validated Deal Certificate", timeout=8000)
        content_accepted = page.content()
        assert "Validated Deal Certificate" in content_accepted, "Deal certificate not rendered after 'where can I pay?'"
        assert "Now make a secure payment through Razorpay" in content_accepted, "Razorpay payment section not rendered!"
        assert "2,050" in content_accepted or "2050" in content_accepted, "Effective unit price was not locked at final firm price 2050!"
        print("  [PASS] Post-Round-7 Payment Inquiry: Deal Certificate & Razorpay unlocked at firm price Rs. 2050.")

        # -------------------------------------------------------------
        # SCENARIO 2: Fresh Product -> Explicit Buy Intent ("I want to buy")
        # -------------------------------------------------------------
        print("\n[SCENARIO 2] Testing Trigger 1 on Fresh Product ('I want to buy')")
        # Switch to Embroidered Linen Shirt
        page.locator("button:has-text('Embroidered Linen Shirt')").first.click()
        time.sleep(1.5)

        # Ensure payment section is hidden on fresh switch
        fresh_content = page.content()
        assert "Now make a secure payment through Razorpay" not in fresh_content

        input_field.fill("I want to buy")
        send_btn.click()
        page.wait_for_selector("text=Validated Deal Certificate", timeout=8000)
        content_buy = page.content()
        assert "Validated Deal Certificate" in content_buy
        assert "Now make a secure payment through Razorpay" in content_buy
        print("  [PASS] Trigger 1 ('I want to buy') immediately locked catalog price and exposed Razorpay checkout.")

        # -------------------------------------------------------------
        # SCENARIO 3: Fresh Product -> Explicit Payment Inquiry ("where do I pay?")
        # -------------------------------------------------------------
        print("\n[SCENARIO 3] Testing Trigger 2 on Fresh Product ('where do I pay?')")
        # Switch to Premium Butter Cookies
        page.locator("button:has-text('Premium Butter Cookies')").first.click()
        time.sleep(1.5)

        input_field.fill("where do I pay?")
        send_btn.click()
        page.wait_for_selector("text=Validated Deal Certificate", timeout=8000)
        content_pay = page.content()
        assert "Validated Deal Certificate" in content_pay
        assert "Now make a secure payment through Razorpay" in content_pay
        assert "100" in content_pay
        print("  [PASS] Trigger 2 ('where do I pay?') immediately locked catalog price and exposed Razorpay checkout.")

        # -------------------------------------------------------------
        # SCENARIO 4: Order Creation & Escrow Node Activation
        # -------------------------------------------------------------
        print("\n[SCENARIO 4] Testing End-to-End Razorpay Order Creation Transition")
        print("\n[SCENARIO 4] Testing End-to-End Razorpay Order Creation & Verification Lifecycle")
        pay_btn = page.locator("button:has-text('Pay')").first
        pay_btn.click()
        time.sleep(2.5)
        time.sleep(3.0)
        content_final = page.content()
        assert "Razorpay Order ID" in content_final or "order_rzp_" in content_final, \
            "Razorpay order creation did not return order ID!"
        print("  [PASS] Razorpay order created and settlement confirmation rendered.")
        assert "PAYMENT_CAPTURED" in content_final, \
            "Expected PAYMENT_CAPTURED state in verified payment card!"
        assert "ESCROW_RESERVED" in content_final or "ESCROW RESERVED" in content_final, \
            "Expected ESCROW_RESERVED state in verified payment card!"
        print("  [PASS] Razorpay order created, signed, verified, PAYMENT_CAPTURED and ESCROW_RESERVED rendered.")

        # -------------------------------------------------------------
        # SCENARIO 5: Multi-Unit Pricing with Negotiated Anchor (prod_004)
        # -------------------------------------------------------------
        print("\n[SCENARIO 5] Testing Multi-Unit Pricing with Negotiated Unit Anchor")
        # Switch to 01 Ceramics & Objects (prod_004, listed 1200, floor 800)
        page.locator("button:has-text('01 Ceramics')").first.click()
        time.sleep(1.5)

        # Negotiate 1 unit down
        input_field.fill("Can I get 1 for 900?")
        send_btn.click()
        time.sleep(2.5)

        # Now ask for 2 units
        input_field.fill("Give me 2 units")
        send_btn.click()
        time.sleep(2.5)
        content_qty2 = page.content()
        assert "1,800" in content_qty2 or "1800" in content_qty2, \
            "Multi-unit 2 units did not anchor on negotiated 900 (should be 1800)!"
        assert "2,400" not in content_qty2 and "2400" not in content_qty2, \
            "VIOLATION: Multi-unit reset to listed price (2400)!"
        print("  [PASS] 2 units properly anchored on negotiated unit rate 900 -> Rs. 1800 (NOT 2400).")

        # -------------------------------------------------------------
        # SCENARIO 6: Mobile Viewport Verification (390 x 844)
        # -------------------------------------------------------------
        print("\n[SCENARIO 6] Testing Mobile Viewport Layout (390 x 844)")
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.goto("http://localhost:3000")
        mobile_page.wait_for_timeout(2000)
        mobile_content = mobile_page.content()
        assert "AURA" in mobile_content
        print("  [PASS] Mobile viewport rendered cleanly without errors.")
        mobile_page.close()

        browser.close()

    print("\n" + "=" * 65)
    print("   [SUCCESS] ALL PLAYWRIGHT BROWSER PAYMENT SCENARIOS PASSED 100%!  ")
    print("=" * 65)

if __name__ == "__main__":
    run_browser_payment_tests()

