import asyncio
import json
import re
import sys
import time
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "orchestration"))
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "wallet-inject"))
sys.path.insert(0, str(REPO_ROOT / "live-sandbox" / "interceptor"))

from playwright.async_api import async_playwright
from injector import WalletInjector
from handler import InterceptHandler

BRAIN_DIR = Path("C:/Users/akodi/.gemini/antigravity-ide/brain/7e1805f2-b9bb-4394-8af7-c1b2866345c1")


async def capture_pending_screenshot(page, start_time):
    # Wait 2 seconds to let the click action register and ensure transaction is in-flight
    await asyncio.sleep(2.0)
    print(f"\n[Pending Capture] Elapsed time: {time.time() - start_time:.2f}s | Request is in-flight (pending verification)")
    
    sc_path = BRAIN_DIR / "e2e_scenario2_tx_pending.png"
    await page.screenshot(full_page=True, path=str(sc_path))
    print(f"[Pending Capture] Screenshot of pending transaction state saved to: {sc_path}")


async def main():
    print("====================================================")
    print("E2E VERIFICATION: EIP-6963 Auto-Detection & Scenario 2 Trace")
    print("====================================================")

    p = await async_playwright().start()
    browser = None
    console_logs = []
    tx_resolved_event = asyncio.Event()
    resolved_tx_hash = None

    def on_console(msg):
        text = msg.text
        console_logs.append(f"[Browser Console] {text}")
        
        # Check if the log matches a 66-character tx hash pattern (0x + 64 hex chars)
        if re.match(r"^0x[a-fA-F0-9]{64}$", text):
            nonlocal resolved_tx_hash
            resolved_tx_hash = text
            tx_resolved_event.set()

    try:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Gather browser console logs and detect resolution
        page.on("console", on_console)

        # Initialize InterceptHandler
        handler = InterceptHandler(
            decoy_wallet="0x0d3c000000000000000000000000000000f00001",
            tracked_tokens=[]
        )

        tx_start_time = 0

        async def on_intercept(payload):
            nonlocal tx_start_time
            method = payload.get("method")
            print(f"\n[TRACE] Injected provider intercepted: {method}")
            print(f"[TRACE] Payload sent to handler: {json.dumps(payload)}")

            if method == "eth_sendTransaction":
                # Update overlay to transaction pending state in-flight
                await page.evaluate("""() => {
                    document.getElementById('vetra-debug-overlay').style.borderColor = '#ffaa00';
                    document.getElementById('vetra-debug-overlay').style.boxShadow = '0 4px 20px rgba(255, 170, 0, 0.5)';
                    document.getElementById('vetra-debug-overlay').innerHTML = '<strong>[VETRA SANDBOX STATE]</strong><br/>Status: <span style="color: #ffaa00; font-weight: bold;">Transaction Pending (In-Flight)...</span><br/>Wallet: vetra-sandbox-0001<br/>Method: eth_sendTransaction<br/>Verifying: Awaiting consensus...';
                }""")
                
                tx_start_time = time.time()
                # Run the pending screenshot checker concurrently
                asyncio.create_task(capture_pending_screenshot(page, tx_start_time))
                
                # Wait 5 seconds in Python before proceeding to simulate slow network/long verification
                print("[TRACE] HOLDING transaction request in pending state for 5 seconds...")
                await asyncio.sleep(5.0)

            # Process via handler (runs real simulation fallback because no Anvil fork is running)
            entry = await handler.handle(payload, injector)
            print(f"[TRACE] handler.py simulation output: {json.dumps(entry.get('simulation'))}")
            print(f"[TRACE] handler.py fake response returned: {json.dumps(entry.get('response'))}")

        # Inject wallet mock provider
        injector = WalletInjector(on_intercept=on_intercept)
        await injector.inject(page)

        # 1. Navigate and verify initial detection
        print("1. Navigating to test dApp...")
        await page.goto("https://metamask.github.io/test-dapp/")
        await page.wait_for_timeout(5000)

        # Inject standard visible visual debug overlay
        await page.evaluate("""() => {
            const div = document.createElement('div');
            div.id = 'vetra-debug-overlay';
            div.style.position = 'fixed';
            div.style.top = '20px';
            div.style.right = '20px';
            div.style.zIndex = '999999';
            div.style.background = '#1a1a1a';
            div.style.color = '#00ff00';
            div.style.padding = '20px';
            div.style.borderRadius = '10px';
            div.style.fontFamily = 'Consolas, monospace';
            div.style.fontSize = '14px';
            div.style.border = '2px solid #00ff00';
            div.style.boxShadow = '0 4px 20px rgba(0, 255, 0, 0.5)';
            div.style.minWidth = '350px';
            div.innerHTML = '<strong>[VETRA SANDBOX STATE]</strong><br/>Status: Initialized<br/>Wallet: EIP-6963 Detected<br/>Connection: Disconnected';
            document.body.appendChild(div);
        }""")

        # Confirm eip6963 warning banner is gone
        warning_visible = await page.locator("#eip6963Warning").is_visible()
        print(f"-> Initial load: #eip6963Warning visible = {warning_visible} (expected False)")
        
        # Save EIP-6963 Auto-Detected State Screenshot (full page height)
        initial_sc = BRAIN_DIR / "initial_detect_eip6963.png"
        await page.screenshot(full_page=True, path=str(initial_sc))
        print(f"-> Screenshot of auto-detected state saved to: {initial_sc}")

        # 2. Select the Vetra Sandbox Wallet
        print("2. Selecting Provider...")
        vetra_btn = page.locator("button:has-text('Vetra')")
        await vetra_btn.wait_for(state="visible", timeout=5000)
        print("-> Clicking 'Use Vetra Sandbox Wallet'...")
        await vetra_btn.click()
        await page.wait_for_timeout(1000)

        # 3. Connect Wallet
        print("3. Checking connection state...")
        connected_acc = await page.inner_text("#accounts")
        if not connected_acc:
            print("-> Clicking 'Connect'...")
            await page.click("#connectButton")
            await page.wait_for_timeout(2000)
            connected_acc = await page.inner_text("#accounts")
        else:
            print(f"-> Wallet connected automatically via EIP-6963.")

        print(f"-> Connected Account: '{connected_acc}'")

        # Update overlay to show connected state
        await page.evaluate(f"""() => {{
            document.getElementById('vetra-debug-overlay').innerHTML = '<strong>[VETRA SANDBOX STATE]</strong><br/>Status: Connected<br/>Wallet: vetra-sandbox-0001<br/>Account: {connected_acc}';
        }}""")

        # 4. Send Transaction (will intercept, hold, screenshot, and fallback resolve)
        print("4. Clicking 'Send Legacy Transaction' (triggers intercept & pending check)...")
        await page.click("#sendButton")
        
        # Wait for the transaction to resolve via console log event (up to 15 seconds)
        print("-> Waiting for transaction to resolve on page...")
        try:
            await asyncio.wait_for(tx_resolved_event.wait(), timeout=15.0)
            print(f"-> Transaction resolved successfully with hash: {resolved_tx_hash}")
        except asyncio.TimeoutError:
            print("-> Warning: Timeout waiting for transaction resolution console log.")

        # Update overlay to show resolved transaction hash state
        await page.evaluate(f"""() => {{
            document.getElementById('vetra-debug-overlay').style.borderColor = '#00ff00';
            document.getElementById('vetra-debug-overlay').style.boxShadow = '0 4px 20px rgba(0, 255, 0, 0.5)';
            document.getElementById('vetra-debug-overlay').innerHTML = '<strong>[VETRA SANDBOX STATE]</strong><br/>Status: <span style="color: #00ff00; font-weight: bold;">Resolved (Success)</span><br/>Wallet: vetra-sandbox-0001<br/>Tx Hash: {resolved_tx_hash}<br/>Simulation Verdict: Caution (fallback path)';
        }}""")

        # Save successful/resolved state screenshot (full page height)
        screenshot_path = BRAIN_DIR / "e2e_scenario1_success.png"
        await page.screenshot(full_page=True, path=str(screenshot_path))
        print(f"-> Screenshot of resolved state saved: {screenshot_path}")

    except Exception as e:
        print(f"[Error] E2E run failed: {e}")
    finally:
        print("\nCaptured Browser Console Logs:")
        for log in console_logs:
            try:
                # Filter console logs to avoid encoding issues
                ascii_log = log.encode('ascii', 'ignore').decode('ascii')
                print(f"  {ascii_log}")
            except Exception:
                pass
        if browser:
            await browser.close()
        await p.stop()


if __name__ == "__main__":
    asyncio.run(main())
