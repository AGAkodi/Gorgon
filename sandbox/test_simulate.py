#!/usr/bin/env python3
"""
Phase 5 validation — the demo centerpiece: models a real "claim your
airdrop" drainer attack end to end against the local fork.

Scenario A ("malicious link" flow): a raw calldata payload (as if handed to
the wallet by a phishing site) is decoded first (so a user/agent could see
"this isn't a claim, it's an unlimited approval to X" before signing), the
spender is registered as a known drainer, then the payload is simulated.
Expect: approval detected, unlimited=True, known_drainer=True, critical.

Scenario B (structured call flow): the drainer's claim() is simulated
directly (function_signature + args, the non-decoded input mode). Expect:
full balance drained to the attacker wallet, critical.

Usage: python3 sandbox/test_simulate.py
(requires sandbox/fork/start-evm-fork.sh already running)
"""
import json
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "exploit-intel"))

from deploy_contracts import deploy_sandbox, decoy_wallet_address  # noqa: E402
from decode import decode_calldata  # noqa: E402
from simulate import simulate_call, build_calldata, MAX_UINT256  # noqa: E402
from drainer_registry import is_known_drainer  # noqa: E402

SCHEMA = json.loads((Path(__file__).parent.parent / "schemas" / "simulation.schema.json").read_text())


def validate_shape(report: dict):
    jsonschema.validate(instance=report, schema=SCHEMA)


def main():
    decoy = decoy_wallet_address()
    print(f"Decoy wallet: {decoy}\n")

    setup = deploy_sandbox(decoy)
    token, drainer, attacker = setup["token_address"], setup["drainer_address"], setup["attacker_wallet"]
    print(f"Mock token: {token}\nDrainer contract: {drainer}\nAttacker wallet: {attacker}\n")

    print("=== Scenario A: malicious-link flow (decode first, simulate second) ===")
    raw_calldata = build_calldata("approve(address,uint256)", [drainer, MAX_UINT256])
    decoded = decode_calldata(raw_calldata, decoded_from="https://example-phishing-site.test/claim")
    print(f"Decoded BEFORE simulating: {decoded['method']} args={decoded['args']}")
    assert decoded["method"] == "approve(address,uint256)"

    # deploy_sandbox() auto-registers the drainer via resync_sandbox_test_drainer()
    # so the registry can never go stale across fork restarts
    entry = is_known_drainer(drainer)
    assert entry is not None, "deploy_sandbox should have auto-registered the drainer"
    assert entry["source"] == "sandbox_test_seed"

    report_a = simulate_call(
        chain="evm", decoy_wallet=decoy, target=token, tracked_tokens=[token],
        calldata=raw_calldata, decoded_from=decoded["decoded_from"],
    )
    validate_shape(report_a)
    print(json.dumps(report_a, indent=2))
    assert report_a["approvals"], "expected an approval to be detected"
    approval = report_a["approvals"][0]
    assert approval["unlimited"] is True
    assert approval["known_drainer"] is True
    assert report_a["risk_summary"]["verdict"] == "critical"
    print("PASS: unlimited approval to known drainer correctly flagged critical\n")

    print("=== Scenario B: structured call flow (claim() actually drains) ===")
    report_b = simulate_call(
        chain="evm", decoy_wallet=decoy, target=drainer, tracked_tokens=[token],
        function_signature="claim(address)", args=[token],
    )
    validate_shape(report_b)
    print(json.dumps(report_b, indent=2))
    assert report_b["balance_deltas"], "expected a balance delta from the drain"
    delta = report_b["balance_deltas"][0]
    assert int(delta["amount"]) < 0, "decoy wallet's balance should have decreased"
    assert report_b["risk_summary"]["verdict"] == "critical"
    print("PASS: balance drain correctly flagged critical\n")

    print("All Phase 5 checks passed.")


if __name__ == "__main__":
    main()
