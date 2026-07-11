import asyncio
import sys
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).parent.parent.parent
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

        # Save screenshot
        path = "C:/Users/akodi/.gemini/antigravity-ide/brain/7e1805f2-b9bb-4394-8af7-c1b2866345c1/debug_screenshot.png"
        await page.screenshot(path=path)
        print(f"Screenshot saved to: {path}")

        # Get body html
        html = await page.content()
        print(f"HTML Length: {len(html)}")

        await browser.close()
    finally:
        await p.stop()


if __name__ == "__main__":
    asyncio.run(main())
