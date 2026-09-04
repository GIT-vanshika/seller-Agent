import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:3000")
    page.wait_for_timeout(2000)

    # Click Organic Dark Chocolate Bar
    page.locator("button:has-text('Organic Dark Chocolate Bar')").first.click()
    time.sleep(1.5)

    # Ask trust question to activate evidence
    input_field = page.locator("input[placeholder*='Ask AURA']")
    send_btn = page.locator("button:has-text('Send')")
    input_field.fill("Can you show real unboxing proof of the unwrapped dark chocolate slab and customer review?")
    send_btn.click()
    time.sleep(3)

    screenshot_path = r"C:\Users\vansh\.gemini\antigravity\brain\6e143384-6a6a-40ad-8a14-4218bca56541\prod_006_real_images_screenshot.png"
    page.screenshot(path=screenshot_path, full_page=True)
    print("SUCCESS: Captured screenshot to:", screenshot_path)
    browser.close()

