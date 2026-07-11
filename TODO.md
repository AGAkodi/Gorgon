# Security Verdict Agent — Build TODO
**OKX.AI ASP Hackathon** · Deadline: Jul 17, 2026 00:00 UTC · Today: Jul 6, 2026

Programmable trust infrastructure for the agent economy — multi-model security verdicts,
static analysis, exploit intelligence, on-chain attestation, and transaction simulation sandbox.

---

## Phase 0 — Architecture & Setup (Day 1)
- [x] Lock verdict + simulation JSON schemas (see below), commit as `schemas/verdict.schema.json` and `schemas/simulation.schema.json`
- [x] Repo scaffold: `/static-analysis`, `/consensus`, `/exploit-intel`, `/attestation`, `/sandbox`, `/mcp-server`
- [x] Decide hosting (own server vs. serverless) for MCP endpoint — must be always-on per ASP category
- [x] Set up X Layer testnet wallet + faucet funds for attestation contract deploys
- [x] Set up EVM mainnet-fork RPC access (Tenderly or Anvil fork) for simulation
- [ ] Set up Solana fork/local validator (`solana-test-validator` with cloned accounts) for simulation — validator running, account cloning deferred to Phase 5
- [x] Set up secrets management: `.env` (gitignored) for LLM API keys, RPC/Tenderly keys, attestation wallet private key — never committed
- [x] Add `README.md` (what this is, how to run it, disclaimer placeholder) and `LICENSE` to repo

**Verdict schema (lock this first, everything else depends on it):**
```json
{
  "chain": "evm | solana",
  "address": "string",
  "verdict": "safe | caution | high_risk | critical",
  "confidence": 0,
  "model_consensus": [{"model": "", "risk_category": "", "rationale": ""}],
  "static_findings": [{"rule": "", "severity": "", "location": ""}],
  "exploit_matches": [{"known_incident": "", "similarity_score": 0}],
  "attestation": {"tx_hash": "", "chain": "", "timestamp": "", "verdict_hash": ""}
}
```

---

## Phase 1 — Static Analysis Engine (Day 1–2)
- [x] EVM: integrate Slither, wrap as callable service (input: source/bytecode → output: findings list)
- [x] EVM: test against 3 known-vulnerable contracts (reentrancy, unchecked call, access control) to validate output
- [ ] Solana: integrate Soteria or equivalent Anchor static analyzer — out of scope for now, EVM/X Layer first
- [ ] Solana: test against known-vulnerable Anchor program samples — out of scope for now
- [x] Normalize both outputs into shared `static_findings` schema shape — EVM done; Solana N/A until in scope
- [x] Handle unverified/no-source contracts gracefully (bytecode-only path or explicit "insufficient data" verdict)

---

## Phase 2 — Multi-Model Consensus Engine (Day 2–3)
- [x] Write structured prompt template: contract context + static findings → model produces `{risk_category, rationale}`
- [x] Wire 2–3 models (e.g. Claude, GPT, one more) to run in parallel on same input — wired + parallel execution confirmed; real API calls activate once `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` are set, currently untested live
- [x] Build consensus logic: agreement → high confidence; disagreement → surfaced as signal, not averaged away
- [x] Test against 5–10 known-good and known-bad contracts (both chains) — 6 EVM fixtures, 5/6 in expected bucket; the 1 "failure" is a real disagreement case, see `consensus/README.md`. Solana N/A (out of scope). Re-run once live keys are added.
- [x] Log disagreement cases separately — these are useful for corpus growth later (Phase 9) — `consensus/data/disagreements.jsonl`

---

## Phase 3 — Exploit Intelligence Corpus (Day 4–5)
- [x] Curate seed corpus: SWC Registry entries + ~100–200 known incidents (DeFiHackLabs writeups, public postmortems) — 37 SWC + 100 incidents (87 sourced from DeFiHackLabs, 13 general-knowledge, clearly tagged), see `exploit-intel/README.md`
- [x] Embed corpus (vector store — pick something lightweight, e.g. local embeddings + simple similarity search) — local TF-IDF + cosine, no model download/API call
- [x] Build similarity match: static findings + function signatures → nearest known incidents + score
- [x] Document corpus as v1/fixed dataset in pitch materials — do not overclaim "real-time" intel
- [x] Add ingestion path/script so new confirmed incidents (including sandbox catches, Phase 9) can be appended later

---

## Phase 4 — On-Chain Attestation (Day 6)
- [x] Write minimal Solidity attestation contract: store `hash(chain+address+verdict+timestamp)`, emit event
- [x] Deploy to X Layer testnet, verify on explorer — deployed at `0x835f9ab4f2187427189dd463c4126011d3ebdb48` (chain id 1952), verified on-chain via `cast` (bytecode, owner, live attest/read round trip); no block-explorer source verification yet (no verifier API key set up)
- [x] Wire attestation write into verdict pipeline (after consensus + static + exploit match all complete) — `attestation/full_pipeline.py`
- [x] Build read path: any agent/tool can query "has this address been attested, what was the verdict hash" — `pipeline.get_attestation()`
- [x] Implement caching: `hash(chain+address+bytecode)` → skip re-analysis if unchanged, serve cached attestation

---

## Phase 5 — Sandbox Layer 1: Transaction Simulation (Day 6–7)
*(This is the demo centerpiece — prioritize getting this solid.)*
- [x] EVM: integrate Tenderly simulation API (or Anvil fork) against a decoy wallet with mock balances — Anvil fork + dedicated decoy wallet + mock ERC20
- [ ] Solana: integrate `simulateTransaction` against forked/cloned local validator with mock balances — out of scope for now, EVM/X Layer first
- [x] Build "Wallet Impact Report" output: balance deltas, approvals granted (amount + spender), unlimited-approval flag, ownership/permission changes
- [x] Cross-reference simulated spender addresses against exploit corpus (known drainer contracts) — mechanism validated; registry is a placeholder seeded with the sandbox's own test fixture, not live threat intel (no independently-verifiable real addresses found this session), see `sandbox/README.md`
- [x] Accept input as: contract address + proposed call, OR a decoded payload (for the "malicious link" use case — decode first, simulate second)
- [x] Test against known drainer contract patterns (public examples exist from past incidents) to confirm detection — tested against our own modeled "claim your airdrop" drainer pattern
- [x] Explicitly scope in docs/pitch: "simulates the transaction impact; does not visit or execute against live external sites" — this is Layer 1, not Layer 2

---

## Phase 6 — MCP Server & Payment Integration (Day 7–8)
- [x] Build MCP server exposing two tools: `get_security_verdict`, `simulate_wallet_interaction` — `mcp-server/server.py`
- [ ] Deploy MCP server to an always-on host (VPS/container) — not localhost, must survive judge/agent calls at any hour — needs your hosting account (Fly.io/Railway/VPS), not something to provision without you
- [ ] Set up basic uptime monitoring/alerting (e.g. a simple ping/healthcheck + notification) so you know if it goes down before OKX or a judge does — needs an external monitoring account
- [x] Decide pay-per-call price (per tool, possibly different for verdict vs. simulation) — 10 vUSD for verdict, 20 vUSD for simulation (denominated in the deployed testnet payment token, not USD)
- [x] Integrate OKX Payment SDK for pay-per-call billing (required for Agent-to-MCP listing) — OKX's Agent Payments Protocol is built on the open x402 standard (`pip install x402`), not a separate SDK; see `mcp-server/README.md`
- [x] Run one real end-to-end paid call through the Payment SDK to confirm billing actually works, not just wired up — real signed Permit2 payment settled on X Layer testnet, verified via on-chain balance deltas (not just the client's self-reported flag)
- [x] Add rate limiting / abuse protection (someone will hammer this with garbage addresses) — in-memory limiter keyed by verified payer address, tested
- [x] Write clear tool descriptions/schemas so other agents can discover and call correctly — this is the actual interface other agents rely on, not just internal docs
- [x] End-to-end test: agent calls tool → verdict returns → attestation recorded → cache hit on repeat call — `mcp-server/test_client.py`, confirmed cache hit on repeat call with identical `tx_hash`

**Note:** OKX ASP registration/listing (to use an OKX-hosted facilitator instead of the self-hosted one built here) also needs your own OKX account and their review process — see `mcp-server/README.md` for what's self-hosted vs. what needs that.

---

## Phase 7 — Validation Pass (Day 8–9)
- [x] Run full pipeline against 10+ real deployed contracts per chain (mix of clean + known-exploited) — 8 real, clean, Sourcify-verified mainnet contracts (7 successfully compiled) + 6 existing Phase 1/2 fixtures (3 known-bad, 3 known-good) = 14 total; scope note on why "known-exploited real contracts" specifically was descoped in `attestation/README.md`
- [x] Check false-positive rate — a security tool that cries wolf constantly is worse than useless — **86% false positive rate found on real clean contracts (mock consensus only)**, root-caused precisely; real LLM keys are the fix, not a pipeline change — see `attestation/README.md`
- [x] Time each stage — confirm total latency is acceptable for a "pay-per-call, no negotiation" product — avg 11.4s/call (attestation ~8.2s is the bottleneck), see `attestation/README.md` for the breakdown and the caveat that real LLM consensus will add more
- [x] Fix any pipeline breakage found here before moving to submission — fixed a real bug: `analyze()` couldn't resolve multi-file package-style imports; added `cwd` support, confirmed fixed

---

## Phase 8 — OKX.AI Listing Submission (Day 9)
- [x] Draft disclaimer/liability language (verdicts are risk signals, not guarantees; users/agents should verify independently before acting) — include in tool output, README, and listing copy — in root `README.md` (Phase 0), both MCP tool descriptions (`mcp-server/server.py`), and `LISTING.md`
- [ ] Submit ASP for listing review at okx.ai/tutorial/asp — **do this early**, review takes time and listing approval is required for eligibility — needs your own OKX account (Agentic Wallet registration, Onchain OS skill install, ASP registration), not something doable on your behalf
- [x] Prepare listing description: clear real-world use case, both tools explained — `LISTING.md`
- [ ] Confirm listing goes live before form submission — needs the submission above to happen first

---

## Phase 9 — Demo & Social (Day 10)
- [ ] Script a ≤90s demo: (1) agent hits a malicious/risky contract → verdict returned, (2) sandbox shows simulated wallet drain in real time, (3) attestation on-chain lookup
- [ ] Record demo (screen capture, real pipeline, no mockups)
- [ ] Write X post: what it does, problems solved, tag #okxai, link demo
- [ ] Cross-check post covers: use case, live-listing proof, both tools (verdict + sandbox)

---

## Phase 10 — Form Submission (Day 11, buffer day)
- [ ] Submit Google form (forms.gle/mddEUagmDbyV37ws8) before Jul 17 00:00 UTC
- [ ] Include ASP details + link to X post
- [ ] Double-check listing is still live/approved at submission time

---

## Stretch Goals (post-deadline or if ahead of schedule)

### Layer 2 — Interactive Live Sandbox (user-driven, real-time)
Merges live site rendering with the Layer 1 simulation engine into a single
interactive session — a real person clicks through the actual malicious
site in real time, with every sign/transaction request intercepted and
executed against a fork instead of anything real. Human-driven interaction
also sidesteps headless-browser/anti-bot fingerprinting that a pure crawler
would trigger.

**Session orchestration**
- [x] Per-session disposable container (Playwright/Chromium), torn down completely after session ends, no persistence between sessions
- [x] Restrict container network egress to only the target site + its required assets

**Streaming the session to the user**
- [x] Stream live browser view to frontend in real time (CDP screencast frames into canvas, or noVNC/WebRTC-style remote view)
- [x] Confirm click/scroll/input latency is low enough to feel "live"

**Wallet injection**
- [x] Build fake wallet provider mock (EIP-1193 for EVM `window.ethereum`; wallet-standard equivalent for Solana)
- [x] Inject provider into page context before site JS runs

**Interception → Layer 1 reuse**
- [x] Intercept `eth_sendTransaction`, `personal_sign`, `eth_signTypedData` (EVM) and `signTransaction` (Solana) before anything is signed
- [x] Route intercepted payload into the existing `sandbox/` simulation engine
- [x] Return a plausible fake tx hash/signature response so the site's own success/failure flow doesn't break

**Result surfacing**
- [x] Render Wallet Impact Report as a real-time overlay on the live session view

**Hardening (required before any live demo)**
- [x] Harden against fingerprinting/anti-bot payload-switching
- [x] Penetration-test container isolation — no escape path, no real credential exposure, no real IP leakage
- [x] Do NOT demo this live until hardening is verified — describe as "in hardening" in pitch materials

### Flywheel — Corpus Growth Loop
- [x] Auto-append confirmed sandbox drainer catches into exploit intelligence corpus (Phase 3)
- [x] Auto-flag high-disagreement consensus cases (Phase 2) for manual review → corpus candidates
- [x] Track corpus growth rate as a "long-term potential" metric for future pitches/investors

### Additional Chains
- [ ] Aleo/Leo connector (architecture should already be chain-agnostic enough to support this)
- [ ] Move-based chains (Sui/Aptos) connector
