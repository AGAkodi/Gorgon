import asyncio
import sys
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "orchestration"))
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "wallet-inject"))

from playwright.async_api import async_playwright
from injector import WalletInjector

async def main():
    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        injector = WalletInjector()
        await injector.inject(page)

        print("Navigating...")
        await page.goto("https://metamask.github.io/test-dapp/")
        await page.wait_for_timeout(5000)

        # Print outer HTML of body on load
        html_on_load = await page.locator("body").inner_html()
        print(f"Body length on load: {len(html_on_load)}")
        
        # Check elements
        warning_vis = await page.locator("#eip6963Warning").is_visible()
        print(f"Warning visible: {warning_vis}")

        vetra_btn = page.locator("button:has-text('Vetra')")
        btn_exists = await vetra_btn.count()
        print(f"Vetra button count: {btn_exists}")
        if btn_exists > 0:
            print("Clicking Vetra button...")
            await vetra_btn.click()
            await page.wait_for_timeout(2000)

        accounts = await page.inner_text("#accounts")
        print(f"Accounts text: '{accounts}'")

        # Save HTML to a file to verify content
        with open("live-sandbox/check_state.html", "w", encoding="utf-8") as f:
            f.write(await page.content())
        print("HTML state written to live-sandbox/check_state.html")

        await browser.close()
    finally:
        await p.stop()

if __name__ == "__main__":
    asyncio.run(main())
