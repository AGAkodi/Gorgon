import asyncio
import sys
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "orchestration"))
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "wallet-inject"))

from playwright.async_api import async_playwright
from injector import WalletInjector

BRAIN_DIR = Path("C:/Users/akodi/.gemini/antigravity-ide/brain/7e1805f2-b9bb-4394-8af7-c1b2866345c1")


async def main():
    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[Browser Console] {msg.text}"))

        injector = WalletInjector()
        await injector.inject(page)

        print("Navigating to test dApp...")
        await page.goto("https://metamask.github.io/test-dapp/")
        
        # Wait for page scripts to load and detect provider
        await page.wait_for_timeout(5000)

        # Check if warning banner exists
        warning_visible = await page.locator("#eip6963Warning").is_visible()
        print(f"Warning Banner (#eip6963Warning) visible: {warning_visible}")

        # Check if the EIP-6963 section with buttons is visible
        section_visible = await page.locator("#eip6963").is_visible()
        print(f"EIP-6963 Section (#eip6963) visible: {section_visible}")

        # Print all buttons in #providers
        buttons = await page.locator("#providers button").all()
        print(f"Found {len(buttons)} provider buttons in #providers:")
        for idx, btn in enumerate(buttons):
            text = await btn.inner_text()
            print(f"  - Button {idx+1}: text='{text}'")

        # Take screenshot of the initial load state
        sc_path = BRAIN_DIR / "initial_detect_eip6963.png"
        await page.screenshot(path=str(sc_path))
        print(f"Screenshot of initial detect state saved to: {sc_path}")

        print("\nBrowser Console Logs:")
        for log in console_logs:
            print(f"  {log}")

        await browser.close()
    finally:
        await p.stop()


if __name__ == "__main__":
    asyncio.run(main())
