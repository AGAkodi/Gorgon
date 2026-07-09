"""
On-chain attestation write/read path (Phase 4).

Shells out to `cast` (Foundry) rather than adding a web3.py dependency —
cast is already required for the sandbox fork scripts and is a thin,
well-tested wrapper around exactly the calls needed here.
"""
import json
import subprocess
import time
from datetime import datetime, timezone

import env  # noqa: F401 (loads .env into os.environ on import)
import os

CHAIN_LABEL = "x-layer-testnet"


class AttestationError(Exception):
    pass


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise AttestationError(f"{name} not set in .env")
    return value


def compute_verdict_hash(chain: str, address: str, verdict: str, timestamp: int) -> str:
    """keccak256(abi.encode(chain, address, verdict, timestamp)) — must match
    VetraAttestation.sol's hashing exactly for on-chain lookups to line up.

    Uses abi.encode (length-prefixed), not encodePacked, for the same reason
    the contract's _key() does: two concatenated dynamic strings can
    collide under encodePacked (SWC-133).
    """
    encoded = subprocess.run(
        ["cast", "abi-encode", "f(string,string,string,uint256)", chain, address, verdict, str(timestamp)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return subprocess.run(
        ["cast", "keccak", encoded], capture_output=True, text=True, check=True,
    ).stdout.strip()


def attest(chain: str, address: str, verdict: str, timestamp: int = None) -> dict:
    """Writes the attestation on-chain. Returns the `attestation` object
    shape from schemas/verdict.schema.json."""
    timestamp = timestamp if timestamp is not None else int(time.time())
    verdict_hash = compute_verdict_hash(chain, address, verdict, timestamp)

    contract = _require_env("ATTESTATION_CONTRACT_ADDRESS")
    rpc_url = _require_env("X_LAYER_TESTNET_RPC_URL")
    private_key = _require_env("ATTESTATION_WALLET_PRIVATE_KEY")

    result = subprocess.run(
        ["cast", "send", contract, "attest(string,string,bytes32)", chain, address, verdict_hash,
         "--rpc-url", rpc_url, "--private-key", private_key, "--json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AttestationError(f"attest() failed: {result.stderr}")

    receipt = json.loads(result.stdout)
    if receipt.get("status") != "0x1":
        raise AttestationError(f"attest() transaction reverted: {receipt}")

    # verdict_hash embeds the timestamp we computed it with; block_timestamp
    # is the actual on-chain mining time (always a few seconds later) — the
    # attestation object's "timestamp" reports the chain-verifiable one, to
    # stay consistent with what get_attestation() reads back.
    block_timestamp = subprocess.run(
        ["cast", "block", receipt["blockNumber"], "--field", "timestamp", "--rpc-url", rpc_url],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    return {
        "tx_hash": receipt["transactionHash"],
        "chain": CHAIN_LABEL,
        "timestamp": datetime.fromtimestamp(int(block_timestamp), tz=timezone.utc).isoformat(),
        "verdict_hash": verdict_hash,
    }


def get_attestation(chain: str, address: str) -> dict:
    """Read path: has this (chain, address) been attested, and what was the
    verdict hash? Returns {"exists": False} if not."""
    contract = _require_env("ATTESTATION_CONTRACT_ADDRESS")
    rpc_url = _require_env("X_LAYER_TESTNET_RPC_URL")

    result = subprocess.run(
        ["cast", "call", contract, "getAttestation(string,string)(bytes32,uint256,bool)", chain, address,
         "--rpc-url", rpc_url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AttestationError(f"getAttestation() call failed: {result.stderr}")

    lines = result.stdout.strip().splitlines()
    verdict_hash, raw_timestamp, exists = lines[0], lines[1], lines[2]
    exists = exists.strip() == "true"

    if not exists:
        return {"exists": False}

    timestamp = int(raw_timestamp.split()[0])
    return {
        "exists": True,
        "verdict_hash": verdict_hash,
        "chain": CHAIN_LABEL,
        "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
    }
