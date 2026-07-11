"""
Wallet provider injector for the Interactive Live Sandbox (Layer 2).

Uses Playwright's `page.add_init_script()` to inject the EIP-1193 (EVM) and
Solana wallet-standard mock providers into the sandboxed page context BEFORE
any site JavaScript runs. This ensures that when a dApp checks for
`window.ethereum` or `window.solana`, it finds the Vetra mock providers
ready to intercept transaction/signing requests.

Also sets up `page.expose_function("__vetra_intercept", ...)` to receive
intercepted calls back in Python, where they're routed to the Layer 1
simulation engine.
"""

import json
from pathlib import Path
from typing import Callable, Awaitable, Optional

from playwright.async_api import Page

WALLET_INJECT_DIR = Path(__file__).parent
EIP1193_SCRIPT = WALLET_INJECT_DIR / "eip1193_provider.js"
SOLANA_SCRIPT = WALLET_INJECT_DIR / "solana_provider.js"


class WalletInjector:
    """Injects mock wallet providers into a Playwright page."""

    def __init__(
        self,
        decoy_address: str = "0x0d3c000000000000000000000000000000f00001",
        chain_id: str = "0x1",
        solana_pubkey: str = "VeTrA1111111111111111111111111111111111111111",
        on_intercept: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.decoy_address = decoy_address
        self.chain_id = chain_id
        self.solana_pubkey = solana_pubkey
        self._on_intercept = on_intercept
        self._page: Optional[Page] = None

    async def inject(self, page: Page):
        """Inject wallet providers into the page context.

        Must be called BEFORE page.goto() so the init scripts run before
        any site JS.
        """
        self._page = page

        # Set configuration globals BEFORE the provider scripts run
        config_script = f"""
            window.__VETRA_DECOY_ADDRESS = "{self.decoy_address}";
            window.__VETRA_CHAIN_ID = "{self.chain_id}";
            window.__VETRA_SOLANA_PUBKEY = "{self.solana_pubkey}";
        """
        await page.add_init_script(script=config_script)

        # Inject the EVM provider
        await page.add_init_script(path=str(EIP1193_SCRIPT))

        # Inject the Solana provider
        await page.add_init_script(path=str(SOLANA_SCRIPT))

        # Expose the intercept callback function to receive calls from JS
        await page.expose_function("__vetra_intercept", self._handle_intercept)

    async def _handle_intercept(self, payload_json: str):
        """Handle an intercepted wallet call from the page JS.

        Called by the JS providers via window.__vetra_intercept(jsonString).
        Routes to the on_intercept callback if set, otherwise resolves
        with a fallback response.
        """
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return

        request_id = payload.get("requestId")
        method = payload.get("method", "")

        if self._on_intercept:
            # Let the interceptor handler process this
            await self._on_intercept(payload)
        else:
            # No interceptor wired — resolve with a fallback immediately
            await self.resolve_request(request_id, self._fallback_response(method))

    async def resolve_request(self, request_id: int, result):
        """Resolve a pending wallet request in the page JS."""
        if self._page and not self._page.is_closed():
            result_json = json.dumps(result) if not isinstance(result, str) else f'"{result}"'
            try:
                await self._page.evaluate(
                    f"window.__vetra_intercept_resolve({request_id}, '{result_json}')"
                )
            except Exception:
                pass  # Page may have navigated or closed

    async def reject_request(self, request_id: int, error_message: str):
        """Reject a pending wallet request in the page JS."""
        if self._page and not self._page.is_closed():
            try:
                await self._page.evaluate(
                    f'window.__vetra_intercept_reject({request_id}, "{error_message}")'
                )
            except Exception:
                pass

    @staticmethod
    def _fallback_response(method: str):
        """Generate a fallback response when no interceptor is wired."""
        import os
        if method == "eth_sendTransaction":
            return "0x" + os.urandom(32).hex()
        if method in ("personal_sign", "eth_signTypedData_v4", "eth_sign",
                       "eth_signTypedData", "eth_signTypedData_v3"):
            return "0x" + os.urandom(65).hex()
        if method in ("signTransaction", "signMessage"):
            return {"signature": list(os.urandom(64))}
        return None
