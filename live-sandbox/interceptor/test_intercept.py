"""
Tests for Transaction Interception (Sub-Phase 4).

Verifies:
1. Fake response generators produce correct formats.
2. InterceptHandler logs and handles EVM transaction requests.
3. InterceptHandler handles signing requests (personal_sign, eth_signTypedData_v4).
4. InterceptHandler handles Solana signing requests.
5. InterceptHandler gracefully degrades and returns caution/unsupported verdicts
   if Anvil is not active or token tracking is not set up, without crashing.
"""

import asyncio
import re
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "wallet-inject"))

from fake_responses import fake_tx_hash, fake_eth_signature, fake_solana_signature
from handler import InterceptHandler


def test_fake_responses():
    """Verify that fake response generators produce correct formats."""
    print("=== Test: Fake responses ===")

    tx_hash = fake_tx_hash()
    assert re.match(r"^0x[0-9a-fA-F]{64}$", tx_hash), f"Invalid fake tx hash: {tx_hash}"
    print(f"  Fake tx hash: {tx_hash}")

    eth_sig = fake_eth_signature()
    assert re.match(r"^0x[0-9a-fA-F]{130}$", eth_sig), f"Invalid fake ETH signature: {eth_sig}"
    # Verify recovery byte is 27 (1b) or 28 (1c)
    last_two = eth_sig[-2:]
    assert last_two in ("1b", "1c"), f"Invalid ETH signature recovery ID: {last_two}"
    print(f"  Fake ETH signature: {eth_sig}")

    sol_sig = fake_solana_signature()
    # Solana signature base58 is usually 87 or 88 characters long
    assert len(sol_sig) >= 80, f"Solana signature too short: {sol_sig}"
    print(f"  Fake Solana signature: {sol_sig}")

    print("  PASS: Fake responses format check\n")


async def test_intercept_handler_degradation():
    """Verify InterceptHandler gracefully handles EVM transactions without Anvil fork running."""
    print("=== Test: InterceptHandler graceful degradation ===")

    handler = InterceptHandler(
        decoy_wallet="0x0d3c000000000000000000000000000000f00001",
        tracked_tokens=[],  # Empty tracked tokens forces it to skip simulation
    )

    payload = {
        "requestId": 42,
        "method": "eth_sendTransaction",
        "params": [{
            "from": "0x0d3c000000000000000000000000000000f00001",
            "to": "0x1234567890abcdef1234567890abcdef12345678",
            "data": "0xa9059cbb000000000000000000000000999999999999999999999999999999999999999900000000000000000000000000000000000000000000000000000000000000ff",
        }],
        "chain": "evm"
    }

    class MockInjector:
        def __init__(self):
            self.resolved = None
            self.rejected = None

        async def resolve_request(self, req_id, result):
            self.resolved = (req_id, result)

        async def reject_request(self, req_id, err):
            self.rejected = (req_id, err)

    injector = MockInjector()
    entry = await handler.handle(payload, injector)

    # Verify that injector.resolve_request was called with a fake tx hash
    assert injector.resolved is not None, "Injector resolve_request not called"
    assert injector.resolved[0] == 42
    assert re.match(r"^0x[0-9a-fA-F]{64}$", injector.resolved[1])

    # Verify simulation report shows it was intercepted and marked as caution since engine/tokens are not ready
    sim = entry["simulation"]
    assert sim is not None
    assert sim["chain"] == "evm"
    assert sim["target"]["address"] == "0x1234567890abcdef1234567890abcdef12345678"
    assert sim["risk_summary"]["verdict"] == "caution"
    print(f"  Graceful degradation verdict: {sim['risk_summary']['verdict']}")
    print(f"  Headline: {sim['risk_summary']['headline']}")

    print("  PASS: Graceful degradation logic works\n")


async def test_intercept_signing_requests():
    """Verify that signing requests are captured and resolved with fake signatures."""
    print("=== Test: Intercept signing requests ===")

    handler = InterceptHandler()

    class MockInjector:
        def __init__(self):
            self.resolved = None

        async def resolve_request(self, req_id, result):
            self.resolved = (req_id, result)

    injector = MockInjector()

    # EVM sign request
    payload_evm = {
        "requestId": 101,
        "method": "personal_sign",
        "params": ["hello", "0x0d3c000000000000000000000000000000f00001"],
        "chain": "evm"
    }

    entry_evm = await handler.handle(payload_evm, injector)
    assert injector.resolved is not None
    assert injector.resolved[0] == 101
    assert re.match(r"^0x[0-9a-fA-F]{130}$", injector.resolved[1])
    assert entry_evm["simulation"]["type"] == "signing_request"
    print("  EVM signing request handled successfully.")

    # Solana sign transaction request
    injector.resolved = None
    payload_sol = {
        "requestId": 201,
        "method": "signTransaction",
        "params": {"instructions": []},
        "chain": "solana"
    }

    entry_sol = await handler.handle(payload_sol, injector)
    assert injector.resolved is not None
    assert injector.resolved[0] == 201
    assert "signature" in injector.resolved[1]
    assert entry_sol["simulation"]["type"] == "solana_sign_request"
    print("  Solana signing request handled successfully.")

    print("  PASS: Signing requests capture works\n")


async def test_flywheel_auto_capture():
    print("=== Test: Flywheel auto-capture ===")
    
    import handler as interceptor_module
    
    # Save original simulate_call
    orig_simulate = getattr(interceptor_module, "simulate_call", None)
    
    # Set mock simulate_call
    def mock_simulate(*args, **kwargs):
        return {
            "chain": "evm",
            "target": {"address": "0xattack_target_111", "method": "claim"},
            "balance_deltas": [{"asset": "USDC", "amount": "-1000", "usd_value": 1000}],
            "approvals": [{"spender": "0xattack_spender_222", "asset": "USDC", "amount": "unlimited", "unlimited": True}],
            "risk_summary": {"verdict": "critical", "headline": "Drain caught!"}
        }
    
    interceptor_module.simulate_call = mock_simulate
    interceptor_module.SIMULATION_AVAILABLE = True
    
    handler = InterceptHandler(
        decoy_wallet="0x0d3c000000000000000000000000000000f00001",
        tracked_tokens=["0xmock_token"],
    )
    
    payload = {
        "requestId": 999,
        "method": "eth_sendTransaction",
        "params": [{
            "from": "0x0d3c000000000000000000000000000000f00001",
            "to": "0xattack_target_111",
            "data": "0x123",
        }],
        "chain": "evm"
    }
    
    # Run interception
    await handler.handle(payload)
    
    # Restore original simulate_call
    if orig_simulate:
        interceptor_module.simulate_call = orig_simulate
    else:
        delattr(interceptor_module, "simulate_call")
    
    # Verify spender and target were added to drainer registry
    from drainer_registry import is_known_drainer
    spender_entry = is_known_drainer("0xattack_spender_222")
    target_entry = is_known_drainer("0xattack_target_111")
    
    assert spender_entry is not None, "Spender was not registered by flywheel"
    assert target_entry is not None, "Target was not registered by flywheel"
    print("  Flywheel correctly registered spender & target in drainer registry.")
    
    # Verify incident was ingested to incidents corpus
    import json
    from pathlib import Path
    incidents_path = Path(__file__).parent.parent.parent / "exploit-intel" / "corpus" / "incidents.json"
    incidents = json.loads(incidents_path.read_text())
    
    has_catch = any("0xattack_target_111" in (entry.get("reference") or "") for entry in incidents)
    assert has_catch, "Incident was not appended to incidents corpus"
    print("  Flywheel correctly appended new catch to incidents corpus.")
    
    # Cleanup registered items for clean subsequent test runs
    from drainer_registry import REGISTRY_PATH
    entries = json.loads(REGISTRY_PATH.read_text())
    entries = [e for e in entries if e["address"] not in ("0xattack_spender_222", "0xattack_target_111")]
    REGISTRY_PATH.write_text(json.dumps(entries, indent=2))
    
    incidents = [i for i in incidents if "0xattack_target_111" not in (i.get("reference") or "")]
    incidents_path.write_text(json.dumps(incidents, indent=2))
    
    print("  PASS: Flywheel auto-capture works\n")


async def main():
    print("Transaction Interception Tests (Sub-Phase 4)\n")

    test_fake_responses()
    await test_intercept_handler_degradation()
    await test_intercept_signing_requests()
    await test_flywheel_auto_capture()

    print("All Interception tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
