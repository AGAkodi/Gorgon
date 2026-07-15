# Vetra

Multi-chain security verdict agent for the AI agent economy. Vetra combines
multi-model AI consensus, static analysis, exploit intelligence matching, and
on-chain attestation with a transaction-simulation sandbox, so agents can
verify before they execute. Built as an OKX.AI Agent-to-MCP service.

Two capabilities anchor the product:

- **Verdict Engine** — static analysis + multi-model consensus + exploit
  intelligence matching + on-chain attestation for any EVM or Solana
  address.
- **Simulation Sandbox** — transaction simulation showing exact wallet
  impact (balance changes, approvals, ownership transfers) before signing.

## Repo layout

```text
schemas/          verdict.schema.json + simulation.schema.json (source of truth)
static-analysis/  EVM (Slither) + Solana (Soteria/Anchor) analyzers
consensus/        multi-model consensus engine
exploit-intel/    exploit intelligence corpus + similarity search
attestation/      on-chain attestation contract + read/write path
sandbox/          transaction simulation engine (Layer 1)
mcp-server/       MCP server exposing get_security_verdict + simulate_wallet_interaction
frontend/         Vetra web UI (marketing site, Verdict Dashboard, Sandbox)
```

Build sequencing and phase-by-phase tasks live in `TODO.md`.

## Running locally

The frontend calls a separate backend (`mcp-server/auth_server.py`) directly
at `http://localhost:4023` — both need to be running, or wallet connect
fails with a "Failed to fetch" / "could not reach the auth server" error.

```sh
# Terminal 1 — backend (wallet auth, API keys, verdict/simulate proxying)
python3 mcp-server/auth_server.py

# Terminal 2 — frontend
cd frontend
pnpm install
pnpm dev
```

For `simulate_wallet_interaction` calls specifically, the sandbox fork also
needs to be running (`sandbox/fork/start-evm-fork.sh`).

## Secrets

Copy `.env.example` to `.env` and fill in LLM API keys, RPC/Tenderly keys, and
the attestation wallet private key. `.env` is gitignored and must never be
committed.

## Disclaimer

Vetra verdicts and simulations are risk signals, not guarantees. They are
produced by automated static analysis, LLM consensus, and simulated
transaction execution, all of which can be wrong, incomplete, or stale.
Agents and users should verify independently before signing or executing
any transaction. Vetra is not liable for losses resulting from reliance on
its output.