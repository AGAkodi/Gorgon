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

        intercepted = []

        async def on_intercept(payload):
            intercepted.append(payload)
            print(f"[Python Intercepted] {payload}")

        injector = WalletInjector(on_intercept=on_intercept)
        await injector.inject(page)

        await page.goto("about:blank")

        # Check request accounts
        print("Calling eth_requestAccounts...")
        res = await page.evaluate("window.ethereum.request({ method: 'eth_requestAccounts' })")
        print("Result:", res)
        print("Intercepted list:", intercepted)

        await browser.close()
    finally:
        await p.stop()


if __name__ == "__main__":
    asyncio.run(main())
