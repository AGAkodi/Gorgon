#!/usr/bin/env python3
"""
Phase 6 end-to-end validation: a real agent-side payment flow against the
live MCP server + self-hosted facilitator on X Layer testnet. Adapted from
OKX's own reference client (examples/python/clients/mcp/simple.py in
github.com/okx/x402).

Calls the free health tool, then get_security_verdict (paid) against one of
our Phase 1 fixtures, confirming a real on-chain settlement transaction.

Usage: python3 mcp-server/test_client.py
Requires: facilitator.py and server.py already running.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
import env  # noqa: E402,F401 (loads .env)

from eth_account import Account  # noqa: E402
from pricing_config import VERDICT_PRICE_WEI
from mcp import ClientSession  # noqa: E402
from mcp.client.sse import sse_client  # noqa: E402

from x402 import x402ClientSync  # noqa: E402
from x402.mechanisms.evm import EthAccountSigner  # noqa: E402
from x402.mechanisms.evm.exact.register import register_exact_evm_client  # noqa: E402
from x402.mcp import MCPToolResult, x402MCPClient  # noqa: E402

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:4021")
TEST_PAYER_PRIVATE_KEY = os.environ.get("TEST_PAYER_PRIVATE_KEY")

if not TEST_PAYER_PRIVATE_KEY:
    print("TEST_PAYER_PRIVATE_KEY not set in .env")
    sys.exit(1)

FIXTURE_PATH = Path(__file__).parent.parent / "static-analysis" / "evm" / "fixtures" / "Reentrancy.sol"


class MCPClientAdapter:
    """Async adapter wrapping mcp.ClientSession for x402MCPClient."""

    def __init__(self, session: ClientSession):
        self._session = session

    async def connect(self, transport: Any) -> None:
        pass

    async def close(self) -> None:
        pass

    async def call_tool(self, params: dict[str, Any], **kwargs: Any) -> MCPToolResult:
        name = params.get("name", "")
        args = params.get("arguments", {})
        meta = params.get("_meta")

        result = await self._session.call_tool(name=name, arguments=args or {}, meta=meta)

        content = []
        for item in result.content:
            if hasattr(item, "text"):
                content.append({"type": "text", "text": item.text})
            else:
                content.append({"type": getattr(item, "type", "text"), "text": str(item)})

        meta_dict = dict(result.meta) if getattr(result, "meta", None) else {}
        return MCPToolResult(
            content=content,
            is_error=getattr(result, "isError", False) or getattr(result, "is_error", False),
            meta=meta_dict,
        )

    async def list_tools(self) -> Any:
        return await self._session.list_tools()


def _text_of(result: MCPToolResult) -> str:
    if not result.content:
        return ""
    first = result.content[0]
    return first.get("text", str(first)) if isinstance(first, dict) else str(first)


def _token_balance(address: str) -> int:
    """Reads the payment token balance directly on-chain via cast — the
    strongest available proof that settlement actually happened, since it
    doesn't depend on the client library's self-reported receipt."""
    out = subprocess.run(
        ["cast", "call", os.environ["PAYMENT_TOKEN_ADDRESS"], "balanceOf(address)(uint256)", address,
         "--rpc-url", os.environ["X_LAYER_TESTNET_RPC_URL"]],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(out.split()[0])


async def main():
    account = Account.from_key(TEST_PAYER_PRIVATE_KEY)
    print(f"Test payer wallet: {account.address}\n")

    payment_client = x402ClientSync()
    register_exact_evm_client(payment_client, EthAccountSigner(account))

    async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Connected to Vetra MCP server.\n")

            adapter = MCPClientAdapter(session)

            def on_payment_requested(context: Any) -> bool:
                price = context.payment_required.accepts[0]
                print(f"Payment required for tool: {context.tool_name}")
                print(f"  amount: {price.amount} (asset {price.asset})")
                print(f"  network: {price.network}")
                print("  signing and paying...\n")
                return True

            x402_mcp = x402MCPClient(
                adapter, payment_client, auto_payment=True, on_payment_requested=on_payment_requested,
            )

            print("=== Discovering tools ===")
            tools_result = await adapter.list_tools()
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description[:80]}...")
            print()

            print("=== Test 1: free health tool ===")
            health_result = await x402_mcp.call_tool("health", {})
            print(f"Response: {_text_of(health_result)}")
            print(f"Payment made: {health_result.payment_made}\n")
            assert _text_of(health_result) == "ok"
            assert health_result.payment_made is False

            print("=== Test 2: get_security_verdict (paid) ===")
            payer_address = account.address
            pay_to_address = Account.from_key(os.environ["ATTESTATION_WALLET_PRIVATE_KEY"]).address
            price = int(VERDICT_PRICE_WEI)  # must match VERDICT_PRICE in server.py

            balance_before_payer = _token_balance(payer_address)
            balance_before_payto = _token_balance(pay_to_address)

            source = FIXTURE_PATH.read_text()
            verdict_result = await x402_mcp.call_tool(
                "get_security_verdict",
                {"chain": "evm", "address": "0xE2ETestReentrancy0000000000000001", "source_code": source},
            )
            print(f"Response: {_text_of(verdict_result)}")
            print(f"Payment made: {verdict_result.payment_made}")
            # Note: verdict_result.payment_response comes back None in this
            # x402 SDK version (2.14.0) — the settlement metadata isn't
            # threaded through to the client result in this code path. Rather
            # than trust a receipt object that may itself have a gap, verify
            # the strongest available signal instead: the actual on-chain
            # balance change.
            print(f"payment_response (informational, may be None — see comment above): {verdict_result.payment_response}")

            balance_after_payer = _token_balance(payer_address)
            balance_after_payto = _token_balance(pay_to_address)
            print("\nOn-chain balance check (the real proof):")
            print(f"  payer:  {balance_before_payer} -> {balance_after_payer} (delta {balance_after_payer - balance_before_payer})")
            print(f"  pay_to: {balance_before_payto} -> {balance_after_payto} (delta {balance_after_payto - balance_before_payto})")
            assert balance_before_payer - balance_after_payer == price, "payer should have paid exactly the quoted price"
            assert balance_after_payto - balance_before_payto == price, "pay_to should have received exactly the quoted price"

            verdict_data = json.loads(_text_of(verdict_result))
            print(f"\nVerdict: {verdict_data['verdict']} (confidence {verdict_data['confidence']})")
            assert verdict_data["verdict"] in ("safe", "caution", "high_risk", "critical")
            assert verdict_result.payment_made is True

            print("\n=== Test 3: simulate_wallet_interaction (paid) ===")
            print("(requires sandbox/deploy_contracts.py already run against a live fork)")
            sim_result = await x402_mcp.call_tool(
                "simulate_wallet_interaction",
                {
                    "chain": "evm",
                    "decoy_wallet": "0x252640910FD5c7aE150058CC9871B4C87ab2F7A1",
                    "target": "0xb45052dd52e14591c5cb4307e8fbd4bc11608f20",
                    "tracked_tokens": ["0xb45052dd52e14591c5cb4307e8fbd4bc11608f20"],
                    "function_signature": "approve(address,uint256)",
                    "args": [
                        "0x5f401c9cf95cb75bc8b28981d3d77b6513ad652a",
                        "115792089237316195423570985008687907853269984665640564039457584007913129639935",
                    ],
                },
            )
            print(f"Response: {_text_of(sim_result)}")
            print(f"Payment made: {sim_result.payment_made}")
            sim_data = json.loads(_text_of(sim_result))
            print(f"Risk summary: {sim_data['risk_summary']}")
            assert sim_result.payment_made is True
            assert sim_data["approvals"], "expected an approval to be detected"

            print("\nAll Phase 6 end-to-end checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
