# Vetra — OKX.AI ASP Listing Draft

Draft copy for submitting Vetra as an Agent Service Provider at
`okx.ai/tutorial/asp`. Everything below is ready to paste into the listing
form once you've registered your Agentic Wallet and OKX account — that
registration and the actual submission need to happen from your account,
not something that can be done on your behalf.

## Name

Vetra

## One-line description

A security verdict and transaction simulation service for AI agents —
know what a contract will do to a wallet before signing, not after.

## What it is

Vetra is programmable trust infrastructure for the agent economy. Before
an AI agent interacts with a smart contract or signs a transaction, it can
call Vetra to get a multi-model security verdict on the contract, or
simulate the exact wallet impact of a proposed transaction — both before
committing anything on a real chain.

## Real-world use case

An AI agent is about to execute a transaction on a user's behalf — approve
a token spend, interact with an unfamiliar contract, or follow a link a
user pasted into a chat. Instead of signing blind, the agent calls Vetra
first:

1. **`get_security_verdict`** — is this contract itself safe? Vetra runs
   static analysis (Slither), multi-model LLM consensus, and exploit
   intelligence matching against a corpus of known incidents, then records
   the verdict on-chain so any agent can later verify it was checked
   without re-running the analysis.
2. **`simulate_wallet_interaction`** — if the agent signs this specific
   transaction, what actually happens to the wallet? Vetra simulates it
   against an isolated decoy wallet and reports the real impact: balance
   changes, approvals granted (and whether they're unlimited), ownership
   changes, and whether the counterparty matches a known drainer pattern.
   This is exactly the check that catches "claim your airdrop" drainer
   scams before the approval is ever signed for real.

Both tools are pay-per-call via x402 on X Layer — no negotiation, no
account setup for the calling agent beyond having funds to pay per call.

## Tools

### `get_security_verdict`

**Input:** `chain` (`"evm"`), `address` (contract address), `source_code`
(optional — Solidity source if the caller has it; without it, Vetra
returns an explicit `insufficient_data` result rather than guessing at a
bytecode-only contract).

**Output:** overall verdict (`safe` / `caution` / `high_risk` /
`critical`), confidence score, per-model consensus breakdown (with
disagreement surfaced explicitly, not averaged away), static analysis
findings, exploit intelligence matches, and an on-chain attestation
(transaction hash + verdict hash) any agent can look up later.

**Price:** 10 vUSD per call (X Layer testnet payment token; see pricing
note below).

### `simulate_wallet_interaction`

**Input:** `chain` (`"evm"`), `decoy_wallet`, `target` (contract being
called), `tracked_tokens` (ERC20s to watch), and either a structured call
(`function_signature` + `args`) or raw `calldata` — the latter supports
the "decode a suspicious link's payload, then simulate it" workflow.

**Output:** balance deltas, approvals granted (amount, spender, whether
unlimited, whether the spender matches a known drainer address), ownership
changes, and a risk verdict with a plain-language headline.

**Price:** 20 vUSD per call — simulation runs a real fork execution, not
just static analysis + LLM calls, so it costs more than a verdict.

## Pricing note

Prices above are denominated in Vetra's own testnet payment token (vUSD),
since this is currently running on X Layer testnet, not mainnet. The
pay-per-call mechanism (x402, settled via Permit2) is real and has been
validated end-to-end with a real signed payment and on-chain settlement —
see `mcp-server/README.md`. Mainnet pricing (in a real stablecoin) is a
decision for closer to mainnet launch, not fixed here.

## Chain support

EVM. Attestation and payment settlement run on X Layer testnet today.
Solana is intentionally out of scope for the initial listing (the
underlying schemas already support it for later — see `TODO.md`).

## Disclaimer

Vetra verdicts and simulations are risk signals, not guarantees. They are
produced by automated static analysis, LLM consensus, and simulated
transaction execution, all of which can be wrong, incomplete, or stale.
Agents and users should verify independently before signing or executing
any transaction. Vetra is not liable for losses resulting from reliance on
its output.

## Links

- Repo: (add your repo URL once public)
- Demo: (add once Phase 9's demo recording exists)
- X post: (add once Phase 9's post is live)

## Status

**Not yet submitted.** Submitting requires your own OKX account: register
an Agentic Wallet, install the Onchain OS skill, register as an ASP
(pay-per-call / A2MCP mode), then submit this listing for review. Do this
early — review takes time and approval is required before the Phase 10
form submission deadline (Jul 17, 2026 00:00 UTC).
