"""
Interception handler for the Interactive Live Sandbox (Layer 2).

Receives intercepted wallet calls from the wallet injection layer (via
the WalletInjector's on_intercept callback), routes EVM transaction
payloads into the existing Layer 1 simulation engine (sandbox/simulate.py),
and returns fake responses to the page so its flow continues.

This module IMPORTS sandbox/simulate.py — it does NOT duplicate simulation
logic.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "sandbox"))
sys.path.insert(0, str(REPO_ROOT / "exploit-intel"))
from drainer_registry import register_drainer, is_known_drainer  # noqa: E402
from ingest import ingest  # noqa: E402
from fake_responses import fake_tx_hash, fake_eth_signature, fake_solana_signature  # noqa: E402

# Graceful import: simulate_call may fail if Anvil fork is not running,
# but the handler should still work (returns fake responses without simulation)
try:
    from simulate import simulate_call, SimulationError  # noqa: E402
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    SimulationError = Exception


# Default decoy wallet for simulations (same as sandbox/ uses)
DEFAULT_DECOY_WALLET = os.environ.get(
    "SANDBOX_DECOY_WALLET_ADDRESS",
    "0x0d3c000000000000000000000000000000f00001"
)

# Default ERC20 tokens to track during simulation
DEFAULT_TRACKED_TOKENS = os.environ.get(
    "SANDBOX_TRACKED_TOKENS",
    ""
).split(",") if os.environ.get("SANDBOX_TRACKED_TOKENS") else []


class InterceptHandler:
    """Handles intercepted wallet calls and routes them through simulation."""

    def __init__(
        self,
        decoy_wallet: str = DEFAULT_DECOY_WALLET,
        tracked_tokens: list = None,
        on_simulation_result: callable = None,
    ):
        self.decoy_wallet = decoy_wallet
        self.tracked_tokens = tracked_tokens or DEFAULT_TRACKED_TOKENS
        self._on_simulation_result = on_simulation_result
        self._interception_log: list = []

    @property
    def interception_log(self) -> list:
        """Returns a list of all intercepted calls and their results."""
        return list(self._interception_log)

    async def handle(self, payload: dict, injector=None):
        """Process an intercepted wallet call.

        Args:
            payload: The intercepted call from the wallet provider JS:
                { "requestId": int, "method": str, "params": ..., "chain": "evm"|"solana" }
            injector: The WalletInjector instance, used to resolve/reject
                the pending JS promise.
        """
        request_id = payload.get("requestId")
        method = payload.get("method", "")
        params = payload.get("params", [])
        chain = payload.get("chain", "evm")

        entry = {
            "requestId": request_id,
            "method": method,
            "chain": chain,
            "params": params,
            "simulation": None,
            "response": None,
        }

        try:
            if method == "eth_sendTransaction":
                result = await self._handle_eth_send_transaction(params)
                entry["simulation"] = result["simulation"]
                entry["response"] = result["fake_response"]

                if injector:
                    await injector.resolve_request(request_id, result["fake_response"])

            elif method in ("personal_sign", "eth_signTypedData",
                            "eth_signTypedData_v3", "eth_signTypedData_v4", "eth_sign"):
                result = self._handle_sign_request(method, params)
                entry["response"] = result["fake_response"]
                entry["simulation"] = {"type": "signing_request", "method": method}

                if injector:
                    await injector.resolve_request(request_id, result["fake_response"])

            elif method == "signTransaction" and chain == "solana":
                result = self._handle_solana_sign(params)
                entry["response"] = result["fake_response"]
                entry["simulation"] = {"type": "solana_sign_request"}

                if injector:
                    await injector.resolve_request(request_id, result["fake_response"])

            elif method == "signMessage" and chain == "solana":
                result = self._handle_solana_sign(params)
                entry["response"] = result["fake_response"]
                entry["simulation"] = {"type": "solana_sign_message"}

                if injector:
                    await injector.resolve_request(request_id, result["fake_response"])

            else:
                # Unknown method — return a generic null
                entry["response"] = None
                if injector:
                    await injector.resolve_request(request_id, None)

        except Exception as e:
            entry["error"] = str(e)
            if injector:
                await injector.reject_request(request_id, str(e))

        self._interception_log.append(entry)

        # Notify listener (streaming server) of the simulation result
        if self._on_simulation_result and entry.get("simulation"):
            await self._on_simulation_result(entry)

        return entry

    async def _handle_eth_send_transaction(self, params) -> dict:
        """Handle an intercepted eth_sendTransaction.

        Extracts the transaction params, calls the Layer 1 simulation
        engine, and returns both the simulation result and a fake tx hash.
        """
        tx_params = params[0] if isinstance(params, list) and params else params
        if isinstance(tx_params, str):
            tx_params = json.loads(tx_params)

        target = tx_params.get("to", "0x0")
        calldata = tx_params.get("data", "0x")

        simulation = None

        if SIMULATION_AVAILABLE and self.tracked_tokens:
            try:
                simulation = simulate_call(
                    chain="evm",
                    decoy_wallet=self.decoy_wallet,
                    target=target,
                    tracked_tokens=self.tracked_tokens,
                    calldata=calldata,
                )
            except SimulationError as e:
                simulation = {
                    "error": str(e),
                    "chain": "evm",
                    "target": {"address": target, "method": "(intercepted)", "calldata": calldata},
                    "risk_summary": {
                        "verdict": "caution",
                        "headline": f"Simulation failed: {e}. Transaction intercepted but could not be analyzed.",
                    },
                }
        else:
            # No simulation available — still capture the interception
            simulation = {
                "chain": "evm",
                "target": {"address": target, "method": "(intercepted)", "calldata": calldata},
                "balance_deltas": [],
                "approvals": [],
                "ownership_changes": [],
                "risk_summary": {
                    "verdict": "caution",
                    "headline": "Transaction intercepted. Simulation engine not available — no impact analysis produced.",
                },
                "decoy_wallet": self.decoy_wallet,
            }

        if simulation and "error" not in simulation:
            risk = simulation.get("risk_summary", {})
            verdict = risk.get("verdict", "safe")
            
            # If critical or high_risk, trigger the flywheel to update threat corpus
            if verdict in ("critical", "high_risk"):
                # Register spender approvals
                for app in simulation.get("approvals", []):
                    spender = app.get("spender")
                    if spender:
                        try:
                            if not is_known_drainer(spender):
                                register_drainer(spender, label=f"Auto-captured Live Sandbox Spend Target: {spender[:10]}", source="sandbox_catch")
                        except Exception as e:
                            print(f"[Flywheel] Failed to register spender: {e}")
                
                # Register target if there is a balance delta decrease
                has_decrease = any(float(d.get("amount", 0)) < 0 for d in simulation.get("balance_deltas", []))
                if has_decrease:
                    try:
                        if not is_known_drainer(target):
                            register_drainer(target, label=f"Auto-captured Live Sandbox Attack Contract: {target[:10]}", source="sandbox_catch")
                    except Exception as e:
                        print(f"[Flywheel] Failed to register target: {e}")
                
                # Ingest incident to corpus
                import time
                try:
                    ingest(
                        name=f"Sandbox Catch {target[:8]} {time.strftime('%H%M%S')}",
                        vulnerability_type="Malicious Wallet Drainer (Sandbox Auto-Catch)",
                        date=time.strftime("%Y-%m-%d", time.gmtime()),
                        loss="N/A (Blocked)",
                        reference=f"Target: {target}",
                        source="sandbox_catch"
                    )
                except Exception as e:
                    print(f"[Flywheel] Failed to ingest incident: {e}")

        return {
            "simulation": simulation,
            "fake_response": fake_tx_hash(),
        }

    def _handle_sign_request(self, method: str, params) -> dict:
        """Handle an intercepted personal_sign / signTypedData.

        These are signing requests (not transactions), so we don't run
        them through the simulation engine — but we do log them and
        return a fake signature.
        """
        return {
            "fake_response": fake_eth_signature(),
            "intercepted_method": method,
            "intercepted_params": params,
        }

    def _handle_solana_sign(self, params) -> dict:
        """Handle an intercepted Solana signTransaction / signMessage."""
        return {
            "fake_response": {"signature": fake_solana_signature()},
            "intercepted_params": params,
        }
