"""
Transaction simulation engine (Phase 5, Layer 1). Runs a proposed call (or
an already-decoded payload) from a decoy wallet against the local EVM fork,
diffs wallet state before/after, and produces the "Wallet Impact Report"
shape defined in schemas/simulation.schema.json.

Explicitly Layer 1: this simulates the transaction's impact against a fork.
It does not visit or execute against any live external site — that's the
(unbuilt, hardening-required) Layer 2 stretch goal.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
import env  # noqa: E402,F401 (loads .env)
import os  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent / "exploit-intel"))
from drainer_registry import is_known_drainer  # noqa: E402

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
OWNERSHIP_TRANSFERRED_TOPIC = "0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0"
MAX_UINT256 = 2**256 - 1

FORK_RPC = os.environ.get("EVM_FORK_RPC_URL", "http://127.0.0.1:8555")


class SimulationError(Exception):
    pass


def _run(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SimulationError(f"command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def _topic_to_address(topic: str) -> str:
    return "0x" + topic[-40:]


def erc20_balance(token: str, wallet: str, rpc_url: str = FORK_RPC) -> int:
    out = _run(["cast", "call", token, "balanceOf(address)(uint256)", wallet, "--rpc-url", rpc_url])
    return int(out.split()[0])


def erc20_allowance(token: str, owner: str, spender: str, rpc_url: str = FORK_RPC) -> int:
    out = _run(["cast", "call", token, "allowance(address,address)(uint256)", owner, spender, "--rpc-url", rpc_url])
    return int(out.split()[0])


def _impersonated_send(sender: str, target: str, calldata: str, rpc_url: str = FORK_RPC) -> dict:
    _run(["cast", "rpc", "--rpc-url", rpc_url, "anvil_impersonateAccount", sender])
    try:
        receipt_json = _run([
            "cast", "send", "--rpc-url", rpc_url, "--from", sender, "--unlocked",
            target, calldata, "--json",
        ])
    finally:
        _run(["cast", "rpc", "--rpc-url", rpc_url, "anvil_stopImpersonatingAccount", sender])
    return json.loads(receipt_json)


def build_calldata(function_signature: str, args: list) -> str:
    return _run(["cast", "calldata", function_signature, *[str(a) for a in args]])


def _parse_logs(logs: list) -> dict:
    transfers, approvals, ownership_changes = [], [], []
    for log in logs:
        topics = log.get("topics", [])
        if not topics:
            continue
        topic0 = topics[0]
        data = log.get("data", "0x")
        value = int(data, 16) if data and data != "0x" else 0

        if topic0 == TRANSFER_TOPIC and len(topics) >= 3:
            transfers.append({
                "token": log["address"],
                "from": _topic_to_address(topics[1]),
                "to": _topic_to_address(topics[2]),
                "value": value,
            })
        elif topic0 == APPROVAL_TOPIC and len(topics) >= 3:
            approvals.append({
                "token": log["address"],
                "owner": _topic_to_address(topics[1]),
                "spender": _topic_to_address(topics[2]),
                "value": value,
            })
        elif topic0 == OWNERSHIP_TRANSFERRED_TOPIC and len(topics) >= 3:
            ownership_changes.append({
                "type": "ownership_transfer",
                "from": _topic_to_address(topics[1]),
                "to": _topic_to_address(topics[2]),
            })
    return {"transfers": transfers, "approvals": approvals, "ownership_changes": ownership_changes}


def simulate_call(
    chain: str,
    decoy_wallet: str,
    target: str,
    tracked_tokens: list,
    function_signature: str = None,
    args: list = None,
    calldata: str = None,
    decoded_from: str = None,
) -> dict:
    """Simulates one call from decoy_wallet to target. Accepts either a
    structured (function_signature, args) call, or raw calldata (the
    "decoded payload" input mode for the malicious-link use case — decode
    the payload into calldata first, pass decoded_from to record where it
    came from).

    tracked_tokens: ERC20 addresses to snapshot balances/allowances for.
    """
    if calldata is None:
        if function_signature is None:
            raise SimulationError("must provide either calldata or function_signature")
        calldata = build_calldata(function_signature, args or [])

    before_balances = {t: erc20_balance(t, decoy_wallet) for t in tracked_tokens}

    receipt = _impersonated_send(decoy_wallet, target, calldata)
    if receipt.get("status") != "0x1":
        raise SimulationError(f"simulated call reverted: {receipt}")

    after_balances = {t: erc20_balance(t, decoy_wallet) for t in tracked_tokens}
    parsed = _parse_logs(receipt.get("logs", []))

    balance_deltas = []
    for token in tracked_tokens:
        delta = after_balances[token] - before_balances[token]
        if delta != 0:
            balance_deltas.append({
                "asset": token,
                "amount": str(delta),
                "usd_value": 0.0,  # no price oracle wired up in the sandbox; left as 0.0 rather than fabricated
            })

    approvals = []
    for a in parsed["approvals"]:
        if a["owner"].lower() != decoy_wallet.lower():
            continue
        drainer_hit = is_known_drainer(a["spender"])
        approvals.append({
            "spender": a["spender"],
            "asset": a["token"],
            "amount": str(a["value"]),
            "unlimited": a["value"] == MAX_UINT256,
            "known_drainer": drainer_hit is not None,
        })

    outbound_recipients = {
        t["to"] for t in parsed["transfers"] if t["from"].lower() == decoy_wallet.lower()
    }
    drainer_recipient = next((r for r in outbound_recipients if is_known_drainer(r)), None)
    drainer_target = target if is_known_drainer(target) else None

    verdict, headline = _risk_summary(
        balance_deltas, approvals, parsed["ownership_changes"], drainer_recipient, drainer_target,
    )

    return {
        "chain": chain,
        "decoy_wallet": decoy_wallet,
        "target": {
            "address": target,
            "method": function_signature or "(decoded calldata)",
            "calldata": calldata,
            **({"decoded_from": decoded_from} if decoded_from else {}),
        },
        "balance_deltas": balance_deltas,
        "approvals": approvals,
        "ownership_changes": parsed["ownership_changes"],
        "risk_summary": {"verdict": verdict, "headline": headline},
    }


def _risk_summary(
    balance_deltas: list, approvals: list, ownership_changes: list,
    drainer_recipient: str = None, drainer_target: str = None,
) -> tuple:
    known_drainer_approval = next((a for a in approvals if a["known_drainer"]), None)
    unlimited_approval = next((a for a in approvals if a["unlimited"]), None)
    negative_delta = any(int(d["amount"]) < 0 for d in balance_deltas)

    if known_drainer_approval:
        return "critical", f"Approval granted to a known drainer address ({known_drainer_approval['spender']})."
    if drainer_recipient:
        return "critical", f"Funds transferred out to a known drainer address ({drainer_recipient})."
    if negative_delta and drainer_target:
        return "critical", f"Balance outflow via a known drainer contract ({drainer_target})."
    if negative_delta:
        # An outflow the wallet didn't directly ask for in this call (e.g. a
        # third party pulling via a prior approval) is high_risk even before
        # we can attribute the recipient to a known drainer — real drains
        # aren't always in the same tx as the approval that enabled them.
        return "high_risk", "Balance decreased during this call; verify the recipient and whether this outflow was intended."
    if ownership_changes:
        return "high_risk", "Ownership or admin permissions changed during this call."
    if unlimited_approval:
        return "caution", "Unlimited approval granted; spender is not on the known-drainer list, but unlimited approvals are inherently higher risk."
    if approvals:
        return "safe", "A limited (non-unlimited) approval was granted to a spender not on the known-drainer list."
    return "safe", "No balance outflow, no approvals, no ownership changes detected."
