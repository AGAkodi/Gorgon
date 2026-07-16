"""
Vetra MCP server (Phase 6): exposes get_security_verdict and
simulate_wallet_interaction to agents over MCP, with x402 pay-per-call
billing settled on X Layer testnet.

Run with: python3 mcp-server/server.py
Requires: mcp-server/facilitator.py running, and (for simulate_wallet_interaction)
the sandbox fork running (sandbox/fork/start-evm-fork.sh).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
sys.path.insert(0, str(Path(__file__).parent.parent / "sandbox"))
sys.path.insert(0, str(Path(__file__).parent.parent / "exploit-intel"))
sys.path.insert(0, str(Path(__file__).parent))

import env  # noqa: E402,F401 (loads .env)
import os  # noqa: E402

from eth_account import Account  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from x402.http import FacilitatorConfig, HTTPFacilitatorClient  # noqa: E402
from x402.mcp import PaymentWrapperHooks, ResourceInfo, create_payment_wrapper  # noqa: E402
from x402.mechanisms.evm.exact import ExactEvmServerScheme  # noqa: E402
from x402.schemas import AssetAmount, ResourceConfig  # noqa: E402
from x402.server import x402ResourceServer  # noqa: E402

from full_pipeline import run_verdict_pipeline  # noqa: E402
from simulate import simulate_call  # noqa: E402
from rate_limit import check_rate_limit  # noqa: E402

# --- Workaround for a bug in x402==2.14.0 (latest on PyPI as of 2026-07-08) ---
# x402.mcp.server._create_payment_required_result calls
# `resource.model_dump(by_alias=True)` on the *mcp-flavored* ResourceInfo
# (x402.mcp.types.ResourceInfo, a plain class), not the pydantic
# x402.schemas.ResourceInfo it should have converted to first (that
# conversion only happens in utils.build_tool_resource_info, which this
# code path doesn't call). Confirmed via traceback: every 402 response —
# including the very first one, built from this module's own default
# ResourceInfo when none is supplied — hits this and crashes with
# `AttributeError: 'ResourceInfo' object has no attribute 'model_dump'`.
# Patching the class in place (rather than vendoring a fork of the SDK)
# since this is the same class object the SDK builds internally too.
def _resource_info_model_dump(self, by_alias: bool = False, exclude_none: bool = False, **_):
    data = {
        "url": self.url,
        "description": self.description,
        "mimeType" if by_alias else "mime_type": self.mime_type,
        "serviceName" if by_alias else "service_name": self.service_name,
        "tags": self.tags,
        "iconUrl" if by_alias else "icon_url": self.icon_url,
    }
    if exclude_none:
        data = {k: v for k, v in data.items() if v is not None}
    return data


ResourceInfo.model_dump = _resource_info_model_dump

PORT = int(os.environ.get("MCP_SERVER_PORT", "4021"))
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "http://127.0.0.1:4022")
NETWORK = os.environ.get("PAYMENT_NETWORK", "eip155:1952")
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN_ADDRESS")

if not PAYMENT_TOKEN:
    print("PAYMENT_TOKEN_ADDRESS not set in .env")
    sys.exit(1)
if not os.environ.get("ATTESTATION_WALLET_PRIVATE_KEY"):
    print("ATTESTATION_WALLET_PRIVATE_KEY not set in .env")
    sys.exit(1)

PAY_TO = Account.from_key(os.environ["ATTESTATION_WALLET_PRIVATE_KEY"]).address

# Pay-per-call pricing (Phase 6). Denominated in our own testnet payment
# token (18 decimals), not USD — see mcp-server/README.md for rationale.
# Simulation costs more: it runs a real fork execution (deploy/impersonate/
# multiple RPC round trips) vs. verdict's static analysis + LLM calls.
from pricing_config import VERDICT_PRICE_WEI as VERDICT_PRICE, SIMULATION_PRICE_WEI as SIMULATION_PRICE

PERMIT2_EXTRA = {"assetTransferMethod": "permit2"}

mcp_server = FastMCP("vetra-mcp-server", host="0.0.0.0", port=PORT)

resource_server = x402ResourceServer(HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL)))
resource_server.register(NETWORK, ExactEvmServerScheme())
# Must happen before build_payment_requirements() below — the resource
# server fetches supported kinds from the facilitator during initialize().
# Not a coroutine function despite the async class (it manages its own
# event loop internally for this one-shot setup call).
resource_server.initialize()

hooks = PaymentWrapperHooks(on_before_execution=check_rate_limit)


def _build_accepts(price: str):
    config = ResourceConfig(
        scheme="exact",
        network=NETWORK,
        pay_to=PAY_TO,
        price=AssetAmount(amount=price, asset=PAYMENT_TOKEN, extra=PERMIT2_EXTRA),
    )
    return resource_server.build_payment_requirements(config)


# ---------------------------------------------------------------------------
# get_security_verdict
# ---------------------------------------------------------------------------

verdict_wrapper = create_payment_wrapper(
    resource_server,
    accepts=_build_accepts(VERDICT_PRICE),
    resource=ResourceInfo(
        url="mcp://tool/get_security_verdict",
        description=(
            "Multi-chain security verdict for an EVM contract: static analysis "
            "(Slither), multi-model LLM consensus, exploit intelligence "
            "matching, and on-chain attestation. Pass the contract source if "
            "known (e.g. from a verified-source lookup) — without it, the "
            "verdict explicitly reports insufficient_data rather than "
            "guessing at bytecode-only contracts."
        ),
        mime_type="application/json",
    ),
    hooks=hooks,
)


@mcp_server.tool(
    name="get_security_verdict",
    description=(
        "Get a security verdict for a smart contract before your agent interacts "
        "with it. Runs static analysis, multi-model AI consensus, and exploit "
        "intelligence matching, and records an on-chain attestation. "
        f"Costs {float(VERDICT_PRICE) / 10**18} vUSD per call (X Layer testnet, "
        "pay-per-call via x402). Args: chain ('evm'), address (contract "
        "address), source_code (Solidity source if you have it — omit for an "
        "explicit insufficient_data result rather than a guess). "
        "Disclaimer: this verdict is a risk signal, not a guarantee — it can "
        "be wrong, incomplete, or stale. Verify independently before signing "
        "or executing any transaction based on it."
    ),
)
@verdict_wrapper
async def get_security_verdict(chain: str, address: str, source_code: str = "") -> dict:
    return await asyncio.to_thread(run_verdict_pipeline, chain, address, source_code)


# ---------------------------------------------------------------------------
# simulate_wallet_interaction
# ---------------------------------------------------------------------------

simulation_wrapper = create_payment_wrapper(
    resource_server,
    accepts=_build_accepts(SIMULATION_PRICE),
    resource=ResourceInfo(
        url="mcp://tool/simulate_wallet_interaction",
        description=(
            "Simulates a proposed contract call (or already-decoded calldata) "
            "against a decoy wallet on an isolated EVM fork, and reports the "
            "wallet impact: balance deltas, approvals granted, unlimited-"
            "approval flag, ownership changes, and a risk verdict. Layer 1 "
            "only — simulates the transaction's impact, does not visit or "
            "execute against any live external site."
        ),
        mime_type="application/json",
    ),
    hooks=hooks,
)


@mcp_server.tool(
    name="simulate_wallet_interaction",
    description=(
        "Simulate what a proposed contract call would do to a wallet, before "
        "signing it for real. Accepts either a structured call (function_signature "
        "+ args) or raw calldata (e.g. decoded from a suspicious link — decode "
        "first, then pass it here to simulate). Runs on an isolated fork against "
        "a decoy wallet; never touches a real wallet or live site. "
        f"Costs {float(SIMULATION_PRICE) / 10**18} vUSD per call (X Layer testnet, "
        "pay-per-call via x402). Args: chain ('evm'), decoy_wallet (address to "
        "simulate from), target (contract being called), tracked_tokens (ERC20 "
        "addresses to watch balances for), function_signature+args OR calldata. "
        "Disclaimer: this is a simulated, isolated-fork risk signal, not a "
        "guarantee — it can be wrong, incomplete, or stale. Verify "
        "independently before signing or executing any transaction based on it."
    ),
)
@simulation_wrapper
async def simulate_wallet_interaction(
    chain: str,
    decoy_wallet: str,
    target: str,
    tracked_tokens: list,
    function_signature: str = None,
    args: list = None,
    calldata: str = None,
) -> dict:
    return await asyncio.to_thread(
        simulate_call, chain, decoy_wallet, target, tracked_tokens, function_signature, args, calldata,
    )


@mcp_server.tool(name="health", description="Free health check — no payment required.")
def health() -> str:
    return "ok"


if __name__ == "__main__":
    print(f"Vetra MCP server running on http://0.0.0.0:{PORT}")
    print(f"  get_security_verdict: {float(VERDICT_PRICE) / 10**18} vUSD/call")
    print(f"  simulate_wallet_interaction: {float(SIMULATION_PRICE) / 10**18} vUSD/call")
    print(f"  facilitator: {FACILITATOR_URL}")
    print(f"  pay_to: {PAY_TO}")
    mcp_server.run(transport="sse")
