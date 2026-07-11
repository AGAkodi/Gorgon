"""
Tests for Wallet Injection (Sub-Phase 3).

Verifies:
1. EIP-1193 provider is injected as window.ethereum before site JS
2. window.ethereum.isMetaMask is true
3. eth_requestAccounts returns the configured decoy address
4. eth_chainId returns the configured chain ID
5. Solana provider is injected as window.solana
6. window.solana.isPhantom is true
7. Intercepted methods (eth_sendTransaction) trigger the callback
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestration"))

from injector import WalletInjector  # noqa: E402

from playwright.async_api import async_playwright  # noqa: E402


DECOY_ADDRESS = "0xdead000000000000000000000000000000beef01"
CHAIN_ID = "0x89"  # Polygon


async def test_evm_provider_injection():
    """Verify EIP-1193 provider injects correctly and responds to basic methods."""
    print("=== Test: EVM provider injection ===")

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        injector = WalletInjector(
            decoy_address=DECOY_ADDRESS,
            chain_id=CHAIN_ID,
        )
        await injector.inject(page)

        # Navigate to a blank page (the init scripts run before any JS)
        await page.goto("data:text/html,<h1>Test</h1>")

        # Check window.ethereum exists and has the right properties
        is_metamask = await page.evaluate("window.ethereum.isMetaMask")
        assert is_metamask is True, f"Expected isMetaMask=true, got {is_metamask}"
        print("  isMetaMask: true")

        is_vetra = await page.evaluate("window.ethereum.isVetraSandbox")
        assert is_vetra is True, f"Expected isVetraSandbox=true, got {is_vetra}"
        print("  isVetraSandbox: true")

        # Test eth_requestAccounts
        accounts = await page.evaluate(
            'window.ethereum.request({ method: "eth_requestAccounts" })'
        )
        assert accounts == [DECOY_ADDRESS.lower()], f"Expected [{DECOY_ADDRESS.lower()}], got {accounts}"
        print(f"  eth_requestAccounts: {accounts}")

        # Test eth_chainId
        chain_id = await page.evaluate(
            'window.ethereum.request({ method: "eth_chainId" })'
        )
        assert chain_id == CHAIN_ID, f"Expected {CHAIN_ID}, got {chain_id}"
        print(f"  eth_chainId: {chain_id}")

        # Test eth_accounts
        accounts2 = await page.evaluate(
            'window.ethereum.request({ method: "eth_accounts" })'
        )
        assert accounts2 == [DECOY_ADDRESS.lower()]
        print(f"  eth_accounts: {accounts2}")

        # Test eth_getBalance
        balance = await page.evaluate(
            'window.ethereum.request({ method: "eth_getBalance", params: ["0x0", "latest"] })'
        )
        assert balance is not None
        print(f"  eth_getBalance: {balance}")

        await browser.close()
    finally:
        await p.stop()

    print("  PASS: EVM provider injection works correctly\n")


async def test_solana_provider_injection():
    """Verify Solana provider injects correctly."""
    print("=== Test: Solana provider injection ===")

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        injector = WalletInjector(
            decoy_address=DECOY_ADDRESS,
            chain_id=CHAIN_ID,
            solana_pubkey="TestPubKey1111111111111111111111111111111111",
        )
        await injector.inject(page)

        await page.goto("data:text/html,<h1>Test</h1>")

        # Check window.solana exists
        is_phantom = await page.evaluate("window.solana.isPhantom")
        assert is_phantom is True, f"Expected isPhantom=true, got {is_phantom}"
        print("  isPhantom: true")

        is_vetra = await page.evaluate("window.solana.isVetraSandbox")
        assert is_vetra is True
        print("  isVetraSandbox: true")

        # Test connect
        result = await page.evaluate("window.solana.connect()")
        pubkey_str = await page.evaluate("window.solana.publicKey.toString()")
        assert pubkey_str == "TestPubKey1111111111111111111111111111111111"
        print(f"  connect publicKey: {pubkey_str}")

        # Test isConnected
        connected = await page.evaluate("window.solana.isConnected")
        assert connected is True
        print(f"  isConnected: {connected}")

        await browser.close()
    finally:
        await p.stop()

    print("  PASS: Solana provider injection works correctly\n")


async def test_intercept_callback():
    """Verify that intercepted methods trigger the on_intercept callback."""
    print("=== Test: Intercept callback ===")

    intercepted_calls = []

    async def on_intercept(payload):
        intercepted_calls.append(payload)
        # Resolve with a fake tx hash
        request_id = payload["requestId"]
        await injector.resolve_request(
            request_id,
            "0xfake_tx_hash_" + "0" * 50
        )

    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        injector = WalletInjector(
            decoy_address=DECOY_ADDRESS,
            chain_id=CHAIN_ID,
            on_intercept=on_intercept,
        )
        await injector.inject(page)

        await page.goto("data:text/html,<h1>Test</h1>")

        # Trigger eth_sendTransaction from the page
        result = await page.evaluate("""
            window.ethereum.request({
                method: "eth_sendTransaction",
                params: [{
                    from: "__DECOY__",
                    to: "0x1234567890abcdef1234567890abcdef12345678",
                    data: "0x12345678",
                    value: "0x0"
                }]
            })
        """.replace("__DECOY__", DECOY_ADDRESS.lower()))

        # Wait a moment for the async callback to process
        await asyncio.sleep(0.5)

        assert len(intercepted_calls) == 1, f"Expected 1 intercepted call, got {len(intercepted_calls)}"
        call = intercepted_calls[0]
        assert call["method"] == "eth_sendTransaction"
        print(f"  Intercepted method: {call['method']}")
        print(f"  Intercepted params: {json.dumps(call['params'], indent=2)[:200]}")
        print(f"  Result returned to page: {result}")

        await browser.close()
    finally:
        await p.stop()

    print("  PASS: Intercept callback works correctly\n")


async def main():
    print("Wallet Injection Tests (Sub-Phase 3)\n")

    await test_evm_provider_injection()
    await test_solana_provider_injection()
    await test_intercept_callback()

    print("All Wallet Injection tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
