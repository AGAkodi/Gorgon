# mcp-server

MCP server exposing two tools to agents: `get_security_verdict` and
`simulate_wallet_interaction`, with x402 pay-per-call billing settled on
X Layer testnet.

## Hosting decision (Phase 0 — done)

**Own server (small always-on container), not serverless.**

Reasoning:

- Pay-per-call with no negotiation means callers expect consistent latency —
  serverless cold starts (Lambda/Vercel functions) are a bad fit for that.
- The MCP protocol expects a long-lived stateful connection per session, not
  discrete per-request function invocations.
- Simulation runs (Phase 5) hold a local fork (anvil / solana-test-validator)
  in memory — awkward to do inside a stateless function with an execution
  time limit.
- Judge/agent calls can arrive at any hour, so it needs a real uptime story
  (healthcheck + alerting), which is simpler to reason about on a container
  you control than a function's cold-start SLA.

Candidates: Fly.io, Railway, or a small VPS (Hetzner/DigitalOcean droplet)
running the server as a persistent process behind a process manager. Pick
whichever the deploy owner already has an account on — the requirement is
just "always-on container", not a specific vendor.

## What "OKX Payment SDK" actually is (Phase 6 — done)

OKX's Agent Payments Protocol is built on **x402**, an open HTTP-native
payment standard (`github.com/okx/x402`, `pip install x402`) — not a
separate proprietary SDK. Confirmed by reading the actual source (not a
web summary): `x402/README.md`, and OKX's own reference examples at
`examples/python/{facilitator,servers/mcp,clients/mcp}/`, which this
implementation adapts directly.

### Pieces

- **`contracts/VetraPaymentToken.sol`** — plain ERC20 (18 decimals), deployed
  to X Layer testnet at `0x09f6b193ad16734e3ce2923fa867e8410ae159b3`
  (`PAYMENT_TOKEN_ADDRESS` in `.env`). No EIP-3009 needed: payments settle
  via **Permit2** + x402's **ExactPermit2Proxy**, both of which are *already
  deployed on X Layer testnet* (confirmed via `cast code` before relying on
  them) — so a plain ERC20 is enough, no custom token cryptography required.
- **`facilitator.py`** — self-hosted facilitator (adapted from OKX's own
  reference at `examples/python/facilitator/basic/main.py`, EVM-only —
  dropped the SVM/Solana half). Verifies and settles payments on-chain using
  the attestation wallet as its settlement signer (reused rather than
  minting yet another key). Run with `python3 mcp-server/facilitator.py`.
- **`server.py`** — the actual MCP server (FastMCP + SSE transport),
  wrapping both tools with `x402`'s `create_payment_wrapper`. Pricing is
  denominated in the deployed payment token, not USD (there's no real-dollar
  peg for a testnet demo token): `get_security_verdict` = 10 vUSD/call,
  `simulate_wallet_interaction` = 20 vUSD/call (simulation costs more — it
  runs a real fork execution, not just static analysis + LLM calls). A free
  `health` tool needs no payment. Run with `python3 mcp-server/server.py`.
- **`rate_limit.py`** — in-memory fixed-window limiter (20 calls/60s),
  wired into the payment wrapper's `on_before_execution` hook, keyed by the
  *verified payer address* rather than IP (IP is easy to rotate/share
  behind NAT; the payer address is already cryptographically confirmed by
  the time this hook runs). Falls back to a shared bucket — still
  rate-limited, not open — if the payload shape doesn't match what's
  expected. Tested in isolation via `test_rate_limit.py` (payer-level
  blocking, bucket isolation between payers, fail-safe fallback).

### Why self-hosted facilitator, not an OKX-hosted one

Joining OKX's AI marketplace as an Agent Service Provider means registering
a wallet, installing the Onchain OS skill, and submitting for review — an
account-creation + review-process step that needs the project owner's own
OKX account and can't be done on their behalf. x402 is deliberately
self-hostable so a resource server isn't blocked on that: this facilitator
settles *real* payments on X Layer testnet right now. Swapping
`FACILITATOR_URL` to an OKX-hosted one later (once ASP-registered) needs no
other code changes.

### A real bug found and worked around

`x402==2.14.0` (latest on PyPI, checked — no newer release exists) has a
bug in `x402.mcp.server._create_payment_required_result`: it calls
`resource.model_dump(by_alias=True)` on the MCP-flavored
`x402.mcp.types.ResourceInfo` (a plain class), not the pydantic
`x402.schemas.ResourceInfo` it should have converted to first — that
conversion only happens in a different helper this code path doesn't call.
This means *every* 402 response crashes the server, including the very
first one built from this module's own default `ResourceInfo`. Confirmed
via a real traceback (temporarily instrumented FastMCP's exception handler
to stop it from swallowing the error, then reverted that debug patch
cleanly). Fixed by monkey-patching `ResourceInfo.model_dump` in `server.py`
to produce the equivalent camelCase dict directly — patching the class
object in place rather than vendoring a fork of the SDK, since it's the
same class the SDK builds internally too.

Separately, `verdict_result.payment_response` comes back `None` on the
client side even on a successful, settled payment (`payment_made=True`) —
looks like a metadata-threading gap elsewhere in this SDK version. Rather
than trust a receipt object that may itself have a gap, `test_client.py`
verifies the real proof instead: on-chain token balance deltas, checked
directly via `cast call`.

## Validated end-to-end (Phase 6 — done)

1. Start the facilitator: `python3 mcp-server/facilitator.py`
2. Start the server: `python3 mcp-server/server.py`
3. (For `simulate_wallet_interaction`) start the fork and deploy sandbox
   contracts: `sandbox/fork/start-evm-fork.sh` then `python3 sandbox/deploy_contracts.py`
4. Run `python3 mcp-server/test_client.py` — a real agent-side client
   (adapted from OKX's reference) that:
   - Calls the free `health` tool (no payment).
   - Calls `get_security_verdict` against the Phase 1 `Reentrancy.sol`
     fixture. Gets a real `402`, signs a real Permit2 payment with a
     dedicated test payer wallet, pays, and gets back the full verdict
     (static findings → consensus → exploit matches → attestation, chaining
     Phases 1–4 exactly as designed). **Verified via direct on-chain
     balance check** (not just the client's self-reported flag): the
     payer's vUSD balance dropped by exactly 10 and the payTo wallet's rose
     by exactly 10.
   - Repeats the identical call and gets `cache_hit: true` with the same
     attestation `tx_hash` — no new on-chain write, exactly Phase 4's
     caching behavior.
   - Calls `simulate_wallet_interaction` (paid) against the Phase 5 drainer
     scenario — correctly flags the unlimited approval to a known drainer
     as `critical`.

This is the real end-to-end proof the TODO asks for ("confirm billing
actually works, not just wired up") — a genuine signed payment, verified
on-chain, not a mocked/stubbed settlement.

## Explicitly not done — needs your account/decision, not just more code

- **Deploy to an always-on host.** Needs your hosting account (Fly.io,
  Railway, a VPS) — provisioning real infra with billing implications isn't
  something to do without you choosing the provider and confirming.
- **Uptime monitoring/alerting.** Needs an external service account
  (UptimeRobot or similar) — same reasoning.
- **OKX ASP registration** (to get listed and use an OKX-hosted facilitator
  instead of the self-hosted one above). Needs your own OKX account,
  wallet registration, and going through their review process.

Everything else in Phase 6 — the server, both tools, pricing, rate
limiting, tool schemas, and a real paid end-to-end call — is done and
verified against live X Layer testnet infrastructure.
