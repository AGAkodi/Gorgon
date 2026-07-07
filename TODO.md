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
- [ ] Write structured prompt template: contract context + static findings → model produces `{risk_category, rationale}`
- [ ] Wire 2–3 models (e.g. Claude, GPT, one more) to run in parallel on same input
- [ ] Build consensus logic: agreement → high confidence; disagreement → surfaced as signal, not averaged away
- [ ] Test against 5–10 known-good and known-bad contracts (both chains) — check for false positives/negatives
- [ ] Log disagreement cases separately — these are useful for corpus growth later (Phase 9)

---

## Phase 3 — Exploit Intelligence Corpus (Day 4–5)
- [ ] Curate seed corpus: SWC Registry entries + ~100–200 known incidents (DeFiHackLabs writeups, public postmortems)
- [ ] Embed corpus (vector store — pick something lightweight, e.g. local embeddings + simple similarity search)
- [ ] Build similarity match: static findings + function signatures → nearest known incidents + score
- [ ] Document corpus as v1/fixed dataset in pitch materials — do not overclaim "real-time" intel
- [ ] Add ingestion path/script so new confirmed incidents (including sandbox catches, Phase 9) can be appended later

---

## Phase 4 — On-Chain Attestation (Day 6)
- [ ] Write minimal Solidity attestation contract: store `hash(chain+address+verdict+timestamp)`, emit event
- [ ] Deploy to X Layer testnet, verify on explorer
- [ ] Wire attestation write into verdict pipeline (after consensus + static + exploit match all complete)
- [ ] Build read path: any agent/tool can query "has this address been attested, what was the verdict hash"
- [ ] Implement caching: `hash(chain+address+bytecode)` → skip re-analysis if unchanged, serve cached attestation

---

## Phase 5 — Sandbox Layer 1: Transaction Simulation (Day 6–7)
*(This is the demo centerpiece — prioritize getting this solid.)*
- [ ] EVM: integrate Tenderly simulation API (or Anvil fork) against a decoy wallet with mock balances
- [ ] Solana: integrate `simulateTransaction` against forked/cloned local validator with mock balances
- [ ] Build "Wallet Impact Report" output: balance deltas, approvals granted (amount + spender), unlimited-approval flag, ownership/permission changes
- [ ] Cross-reference simulated spender addresses against exploit corpus (known drainer contracts)
- [ ] Accept input as: contract address + proposed call, OR a decoded payload (for the "malicious link" use case — decode first, simulate second)
- [ ] Test against known drainer contract patterns (public examples exist from past incidents) to confirm detection
- [ ] Explicitly scope in docs/pitch: "simulates the transaction impact; does not visit or execute against live external sites" — this is Layer 1, not Layer 2

---

## Phase 6 — MCP Server & Payment Integration (Day 7–8)
- [ ] Build MCP server exposing two tools: `get_security_verdict`, `simulate_wallet_interaction`
- [ ] Deploy MCP server to an always-on host (VPS/container) — not localhost, must survive judge/agent calls at any hour
- [ ] Set up basic uptime monitoring/alerting (e.g. a simple ping/healthcheck + notification) so you know if it goes down before OKX or a judge does
- [ ] Decide pay-per-call price (per tool, possibly different for verdict vs. simulation)
- [ ] Integrate OKX Payment SDK for pay-per-call billing (required for Agent-to-MCP listing)
- [ ] Run one real end-to-end paid call through the Payment SDK to confirm billing actually works, not just wired up
- [ ] Add rate limiting / abuse protection (someone will hammer this with garbage addresses)
- [ ] Write clear tool descriptions/schemas so other agents can discover and call correctly — this is the actual interface other agents rely on, not just internal docs
- [ ] End-to-end test: agent calls tool → verdict returns → attestation recorded → cache hit on repeat call

---

## Phase 7 — Validation Pass (Day 8–9)
- [ ] Run full pipeline against 10+ real deployed contracts per chain (mix of clean + known-exploited)
- [ ] Check false-positive rate — a security tool that cries wolf constantly is worse than useless
- [ ] Time each stage — confirm total latency is acceptable for a "pay-per-call, no negotiation" product
- [ ] Fix any pipeline breakage found here before moving to submission

---

## Phase 8 — OKX.AI Listing Submission (Day 9)
- [ ] Draft disclaimer/liability language (verdicts are risk signals, not guarantees; users/agents should verify independently before acting) — include in tool output, README, and listing copy
- [ ] Submit ASP for listing review at okx.ai/tutorial/asp — **do this early**, review takes time and listing approval is required for eligibility
- [ ] Prepare listing description: clear real-world use case, both tools explained
- [ ] Confirm listing goes live before form submission

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

### Layer 2 — Live Link Crawling Sandbox
- [ ] Containerized headless browser (Playwright), fully isolated, disposable per run
- [ ] Burner wallet with zero real value, testnet keys only, no persistent session/IP
- [ ] Capture transaction/signature request generated by the live site
- [ ] Feed captured payload into Layer 1 simulator for impact report
- [ ] Harden against fingerprinting/anti-bot payload-switching before treating as reliable
- [ ] Explicitly do NOT demo this live until hardened — describe as "in hardening" in pitch

### Flywheel — Corpus Growth Loop
- [ ] Auto-append confirmed sandbox drainer catches into exploit intelligence corpus (Phase 3)
- [ ] Auto-flag high-disagreement consensus cases (Phase 2) for manual review → corpus candidates
- [ ] Track corpus growth rate as a "long-term potential" metric for future pitches/investors

### Additional Chains
- [ ] Aleo/Leo connector (architecture should already be chain-agnostic enough to support this)
- [ ] Move-based chains (Sui/Aptos) connector
