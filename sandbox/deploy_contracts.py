"""
Deploys the sandbox's mock contracts to a running local EVM fork and wires
up a decoy wallet with a mock token balance — the "against a decoy wallet
with mock balances" setup Phase 5 asks for.

Requires sandbox/fork/start-evm-fork.sh already running (default
http://127.0.0.1:8555).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
import env  # noqa: E402,F401 (loads .env)
import os  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONTRACTS_DIR = Path(__file__).parent / "contracts"
BUILD_DIR = Path("/tmp/sandbox-build")

FORK_RPC = os.environ.get("EVM_FORK_RPC_URL", "http://127.0.0.1:8555")

# Anvil's well-known default dev account #0 — funded with 10000 test ETH on
# every fork by default. Used only as the deployer on the ephemeral fork.
DEPLOYER_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
# Anvil default dev account #9 — stands in for "the attacker's wallet" in
# the simulated drain.
ATTACKER_WALLET = "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720"

DECOY_WALLET_PK = os.environ.get("SANDBOX_DECOY_WALLET_PRIVATE_KEY")


def _run(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def compile_contracts():
    _run([
        "solc", "--combined-json", "abi,bin",
        str(CONTRACTS_DIR / "MockERC20.sol"),
        str(CONTRACTS_DIR / "DrainerClaim.sol"),
        "-o", str(BUILD_DIR), "--overwrite",
    ])
    return json.loads((BUILD_DIR / "combined.json").read_text())["contracts"]


def _deploy(bytecode_hex: str, constructor_args: list = None, arg_types: str = "") -> str:
    initcode = "0x" + bytecode_hex
    if constructor_args:
        encoded = _run(["cast", "abi-encode", f"f({arg_types})", *constructor_args])
        initcode += encoded[2:]
    receipt_json = _run([
        "cast", "send", "--rpc-url", FORK_RPC, "--private-key", DEPLOYER_PK,
        "--create", initcode, "--json",
    ])
    receipt = json.loads(receipt_json)
    if receipt.get("status") != "0x1":
        raise RuntimeError(f"deployment reverted: {receipt}")
    return receipt["contractAddress"]


def deploy_sandbox(decoy_wallet: str, mock_token_amount: int = 10_000 * 10**18) -> dict:
    contracts = compile_contracts()

    token_bin = contracts["sandbox/contracts/MockERC20.sol:MockERC20"]["bin"]
    token_address = _deploy(token_bin, ["VetraMockUSD", "vUSD"], "string,string")

    drainer_bin = contracts["sandbox/contracts/DrainerClaim.sol:DrainerClaim"]["bin"]
    drainer_address = _deploy(drainer_bin, [ATTACKER_WALLET], "address")

    # Give the decoy wallet gas and a mock token balance.
    _run(["cast", "rpc", "--rpc-url", FORK_RPC, "anvil_setBalance", decoy_wallet, hex(10 * 10**18)])
    _run([
        "cast", "send", "--rpc-url", FORK_RPC, "--private-key", DEPLOYER_PK,
        token_address, "mint(address,uint256)", decoy_wallet, str(mock_token_amount),
    ])

    return {
        "token_address": token_address,
        "drainer_address": drainer_address,
        "attacker_wallet": ATTACKER_WALLET,
        "decoy_wallet": decoy_wallet,
        "fork_rpc": FORK_RPC,
    }


def decoy_wallet_address() -> str:
    if not DECOY_WALLET_PK:
        raise RuntimeError("SANDBOX_DECOY_WALLET_PRIVATE_KEY not set in .env")
    return _run(["cast", "wallet", "address", "--private-key", DECOY_WALLET_PK])


if __name__ == "__main__":
    decoy = decoy_wallet_address()
    result = deploy_sandbox(decoy)
    print(json.dumps(result, indent=2))
