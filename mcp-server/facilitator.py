"""
Self-hosted x402 payment facilitator for X Layer testnet, EVM-only
(adapted from OKX's own reference implementation at
examples/python/facilitator/basic/main.py in github.com/okx/x402 — dropped
the SVM/Solana half, since Solana is out of scope for Vetra right now).

Why self-hosted rather than pointed at an OKX-hosted facilitator: joining
OKX's AI marketplace as an Agent Service Provider means registering a
wallet, installing the Onchain OS skill, and submitting for review — an
account-creation + review-process step that can't be done without the
project owner's OKX account. x402 is an open, self-hostable protocol by
design specifically so a resource server isn't blocked on that: this
facilitator settles real payments on X Layer testnet right now, and
swapping FACILITATOR_URL to an OKX-hosted one later (once ASP-registered)
requires no other code changes.

Run with: python3 mcp-server/facilitator.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
import env  # noqa: E402,F401 (loads .env)
import os  # noqa: E402

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from x402 import x402Facilitator  # noqa: E402
from x402.mechanisms.evm import FacilitatorWeb3Signer  # noqa: E402
from x402.mechanisms.evm.exact import register_exact_evm_facilitator  # noqa: E402
from x402.schemas import PaymentRequirements, SettleResponse, parse_payment_payload  # noqa: E402

PORT = int(os.environ.get("FACILITATOR_PORT", "4022"))
NETWORK = os.environ.get("PAYMENT_NETWORK", "eip155:1952")

if not os.environ.get("ATTESTATION_WALLET_PRIVATE_KEY"):
    print("ATTESTATION_WALLET_PRIVATE_KEY not set in .env")
    sys.exit(1)

# The facilitator's own wallet pays the gas to settle payments on-chain.
# Reuses the attestation wallet — same testnet-only, zero-real-value keypair
# already funded in Phase 0/4, rather than minting yet another one.
signer = FacilitatorWeb3Signer(
    private_key=os.environ["ATTESTATION_WALLET_PRIVATE_KEY"],
    rpc_url=os.environ["X_LAYER_TESTNET_RPC_URL"],
)
print(f"Facilitator settlement wallet: {signer.address}")

facilitator = x402Facilitator()
register_exact_evm_facilitator(facilitator, signer, networks=NETWORK)

app = FastAPI(title="Vetra x402 Facilitator (self-hosted, X Layer testnet)", version="1.0.0")


class VerifyRequest(BaseModel):
    paymentPayload: dict
    paymentRequirements: dict


class SettleRequest(BaseModel):
    paymentPayload: dict
    paymentRequirements: dict


@app.post("/verify")
async def verify(request: VerifyRequest):
    try:
        payload = parse_payment_payload(request.paymentPayload)
        requirements = PaymentRequirements.model_validate(request.paymentRequirements)
        response = await facilitator.verify(payload, requirements)
        return response.model_dump(by_alias=True, exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/settle")
async def settle(request: SettleRequest):
    try:
        payload = parse_payment_payload(request.paymentPayload)
        requirements = PaymentRequirements.model_validate(request.paymentRequirements)
        response = await facilitator.settle(payload, requirements)
        return response.model_dump(by_alias=True, exclude_none=True)
    except Exception as e:
        if "aborted" in str(e).lower():
            abort = SettleResponse(
                success=False, error_reason=str(e),
                network=request.paymentPayload.get("accepted", {}).get("network", "unknown"),
                transaction="",
            )
            return abort.model_dump(by_alias=True, exclude_none=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/supported")
async def supported():
    response = facilitator.get_supported()
    return {
        "kinds": [k.model_dump(by_alias=True, exclude_none=True) for k in response.kinds],
        "extensions": response.extensions,
        "signers": response.signers,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    print(f"Facilitator listening on port {PORT} for network {NETWORK}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
