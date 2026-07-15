"""
On-chain attestation write/read path (Phase 4).

Rewritten to use native Python libraries (eth-account, eth-abi, eth-utils)
and standard JSON-RPC HTTP calls rather than shelling out to cast (Foundry),
ensuring compatibility with systems that do not have Foundry installed.
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
import env  # noqa: F401 (loads .env into os.environ on import)
from eth_account import Account
from eth_utils import keccak, to_checksum_address
import eth_abi
from hexbytes import HexBytes

CHAIN_LABEL = "x-layer-testnet"


class AttestationError(Exception):
    pass


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise AttestationError(f"{name} not set in .env")
    return value


def _rpc_call(rpc_url: str, method: str, params: list) -> dict:
    data = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=data, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            resp = json.loads(res.read().decode("utf-8"))
            if "error" in resp:
                raise AttestationError(f"RPC Error: {resp['error']}")
            return resp["result"]
    except Exception as e:
        raise AttestationError(f"RPC request to {rpc_url} failed: {e}")


def compute_verdict_hash(chain: str, address: str, verdict: str, timestamp: int) -> str:
    """keccak256(abi.encode(chain, address, verdict, timestamp)) — must match
    VetraAttestation.sol's hashing exactly for on-chain lookups to line up.
    """
    encoded = eth_abi.encode(["string", "string", "string", "uint256"], [chain, address, verdict, timestamp])
    return "0x" + keccak(encoded).hex()


def attest(chain: str, address: str, verdict: str, timestamp: int = None) -> dict:
    """Writes the attestation on-chain. Returns the `attestation` object
    shape from schemas/verdict.schema.json."""
    timestamp = timestamp if timestamp is not None else int(time.time())
    verdict_hash = compute_verdict_hash(chain, address, verdict, timestamp)

    contract = _require_env("ATTESTATION_CONTRACT_ADDRESS")
    rpc_url = _require_env("X_LAYER_TESTNET_RPC_URL")
    private_key = _require_env("ATTESTATION_WALLET_PRIVATE_KEY")

    account = Account.from_key(private_key)

    # 1. Get nonce
    nonce = _rpc_call(rpc_url, "eth_getTransactionCount", [account.address, "latest"])
    nonce_val = int(nonce, 16) if isinstance(nonce, str) else nonce

    # 2. Get gas price
    gas_price_hex = _rpc_call(rpc_url, "eth_gasPrice", [])
    gas_price = int(gas_price_hex, 16)

    # 3. Construct calldata
    # attest(string,string,bytes32) -> selector: 2a528198
    selector = bytes.fromhex("2a528198")
    v_hash_bytes = HexBytes(verdict_hash)
    encoded_args = eth_abi.encode(["string", "string", "bytes32"], [chain, address, v_hash_bytes])
    calldata = "0x" + (selector + encoded_args).hex()

    # 4. Construct transaction
    tx = {
        "nonce": nonce_val,
        "to": to_checksum_address(contract),
        "value": 0,
        "gas": 150000,
        "gasPrice": gas_price,
        "data": calldata,
        "chainId": 1952
    }

    # 5. Sign and send
    signed_tx = account.sign_transaction(tx)
    tx_hash = _rpc_call(rpc_url, "eth_sendRawTransaction", ["0x" + signed_tx.raw_transaction.hex()])
    
    # 6. Wait for transaction receipt
    receipt = None
    for _ in range(30):
        try:
            receipt = _rpc_call(rpc_url, "eth_getTransactionReceipt", [tx_hash])
            if receipt:
                break
        except Exception:
            pass
        time.sleep(2)

    if not receipt:
        raise AttestationError("attest() failed: Transaction receipt not found after timeout")

    if int(receipt.get("status", "0x0"), 16) != 1:
        raise AttestationError(f"attest() transaction reverted: {receipt}")

    # 7. Get block timestamp
    block = _rpc_call(rpc_url, "eth_getBlockByNumber", [receipt["blockNumber"], False])
    block_timestamp = int(block["timestamp"], 16)

    return {
        "tx_hash": tx_hash,
        "chain": CHAIN_LABEL,
        "timestamp": datetime.fromtimestamp(block_timestamp, tz=timezone.utc).isoformat(),
        "verdict_hash": verdict_hash,
    }


def get_attestation(chain: str, address: str) -> dict:
    """Read path: has this (chain, address) been attested, and what was the
    verdict hash? Returns {"exists": False} if not."""
    contract = _require_env("ATTESTATION_CONTRACT_ADDRESS")
    rpc_url = _require_env("X_LAYER_TESTNET_RPC_URL")

    # getAttestation(string,string) -> selector: 1b08d114
    selector = bytes.fromhex("1b08d114")
    encoded_args = eth_abi.encode(["string", "string"], [chain, address])
    calldata = "0x" + (selector + encoded_args).hex()

    try:
        resp = _rpc_call(rpc_url, "eth_call", [{"to": contract, "data": calldata}, "latest"])
    except Exception as e:
        raise AttestationError(f"getAttestation() call failed: {e}")

    resp_bytes = HexBytes(resp)
    decoded = eth_abi.decode(["bytes32", "uint256", "bool"], resp_bytes)
    
    verdict_hash = "0x" + decoded[0].hex()
    timestamp = decoded[1]
    exists = decoded[2]

    if not exists:
        return {"exists": False}

    return {
        "exists": True,
        "verdict_hash": verdict_hash,
        "chain": CHAIN_LABEL,
        "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
    }
