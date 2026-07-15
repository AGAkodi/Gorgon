# Vetra — Remaining TODO (post database wiring)

**OKX.AI ASP Hackathon · Deadline: Jul 17, 2026 00:00 UTC**

Assumes Supabase + backend wiring is complete. This picks up from there:
a sanity check on the wiring claims, wallet connect (OKX Wallet, X Layer),
the sandbox wallet, then the remaining path to submission.

---

### Confirmed Done (independently verified on-chain)

- [x] VetraAttestation contract deployed to X Layer testnet — `0x835F9AB4f2187427189dd463C4126011D3eBDB48` (canonical, owner key present in current `.env`), deploy tx Accepted on L2, confirmed directly on OKLink explorer

  Note (updated 2026-07-13): a second deployment at `0x7861C11Db0d154721f1D9D2E36A00A8f6aF68F30` also exists and is also real/verified on-chain. Its owner key briefly landed in `.env` via another session/checkout's overwrite (see "Watch For" below) — so it's no longer strictly true that the key is unavailable — but we deliberately kept `0x835F9AB4...` as canonical anyway: its key was confirmed still recoverable and fully functional (`owner()` unchanged, wallet still funded), and it has the actual verified track record from this session's testing. `0x7861C11D...` remains intentionally unused — do not reference it going forward, do not attempt to migrate to it, and do not silently swap `.env` back to it.

- [x] `ATTESTATION_CONTRACT_ADDRESS` set in `.env` → `0x835F9AB4f2187427189dd463C4126011D3eBDB48`
- [x] Mock payment token deployed to X Layer testnet — `0x0cdFdbA236F256C49eFBcf831Afabfa5F4B6045E`, confirmed via `cast call name()/symbol()` to be genuinely named "Test USDC" / symbol "tUSDC" (this supersedes an earlier, differently-named "Vetra Payment Token"/"vUSD" deployment at a different address from this same session — that one's now superseded, not this one)
- [x] `PAYMENT_TOKEN_ADDRESS` set in `.env` → `0x0cdFdbA236F256C49eFBcf831Afabfa5F4B6045E`
- [x] X Layer testnet chain ID confirmed as 1952 (via raw `eth_chainId` RPC call, cross-checked against ChainList — chain 195 confirmed deprecated/legacy, unrelated to current testnet)
- [x] Attestation pipeline bug fixed — non-checksummed contract address was causing every write to crash (`eth_account` requires checksummed `to`)
- [x] "Always safe" verdict bug fixed — `insufficient_data` flag was being silently dropped and read as "safe"; now correctly short-circuits to "caution," which properly triggers the sandbox popup

---

### New: Watch For — .env Desync Across Sessions

`.env` is correctly gitignored, but that means it never syncs if you (or
Antigravity) work from more than one checkout/worktree — as just happened
with two independent attestation contract deployments. Going forward:

- [ ] If working from multiple machines/worktrees on this repo, manually keep `.env` values in sync yourself — nothing will warn you if they drift
- [ ] Treat any "this doesn't match what I expected" moment as worth checking `.env`'s actual current values first, before assuming a code bug

---

### Immediate Next Check — Attestation Wired Into Live Pipeline

Deployment is confirmed, but whether the verdict pipeline actually CALLS
this contract on a real scan hasn't been checked yet. Do this before
anything else below.

- [x] Run a real `get_security_verdict` scan, get the `attestation.tx_hash` from the response
- [x] Confirm it is NOT all zeros this time
- [ ] Take that tx hash and look it up yourself on the X Layer testnet explorer (`oklink.com/x-layer-testnet/tx/<hash>`) — confirm `Accepted on L2` and that `To` matches `0x835F9AB4f2187427189dd463C4126011D3eBDB48`
- [x] Scan the SAME contract a second time — confirm cache hit reuses the SAME tx hash rather than writing a new one

---

### Phase 1 — Sanity Check Before Building Further

Two questions from the wiring review were never directly answered. Confirm
these now — if either is wrong, everything downstream (RLS-gated pages,
per-wallet API keys) is silently broken, not working.

- [x] Confirm directly: is the custom JWT signed with Supabase's project JWT secret, or registered as a Third-Party Auth provider — so `auth.jwt()` can actually parse `wallet_address`?
- [x] Confirm directly: does the frontend call Supabase directly with an in-memory JWT, or does every Supabase call proxy through the FastAPI backend using the httpOnly cookie?
- [x] Sign in with two different wallets, two separate sessions — confirm Wallet B's API Keys page shows ZERO of Wallet A's keys (real screenshot/trace, not a description)
- [x] Scan the same contract twice — confirm second call shows "Cache Hit" badge, $0 cost (confirmed earlier; re-confirm attestation tx hash reuse now that attestation is live — see "Immediate Next Check" above)

---

### Phase 2 — Real Wallet Connect (replaces placeholder auth trigger)

- [x] Wire "Get Started" (and any other entry point) to open the OKX Wallet connect prompt directly — not a generic WalletConnect modal, OKX Wallet as primary/first option
- [x] On connect: request account access, confirm the app is targeting X Layer (chain ID check — prompt a network switch if the connected wallet is on the wrong chain)
- [x] Feed the connected address into the existing SIWE nonce → sign → login flow already built
- [x] Post-connect: nav updates to show truncated wallet address pill (e.g. `0x4a2f…c91e`), replacing "Get Started"
- [x] Add a disconnect option from that same nav pill
- [x] Confirm this is visually and functionally distinct from the Sandbox wallet (Phase 3) — different label, different color, never in the same UI region

---

### Phase 3 — Sandbox Wallet on X Layer

- [x] Confirm the sandbox decoy wallet (`SANDBOX_DECOY_WALLET_PRIVATE_KEY`) is wired to operate against an X Layer fork, not just a generic EVM/Ethereum mainnet fork — since X Layer is the primary target chain now that Solana's dropped
- [x] Label it explicitly "Sandbox Wallet (Simulated)" with a persistent "SIMULATED" tag, per the earlier UI spec — confirm it never says "Connect Wallet" anywhere
- [x] Confirm mock balances are minted correctly on the X Layer fork for the decoy wallet (native token + relevant test tokens for whatever contract is being simulated)
- [x] Re-confirm interception (`eth_sendTransaction`, `personal_sign`, `eth_signTypedData`) still resolves correctly now that it's pointed at an X Layer fork instead of a general EVM fork — chain-specific quirks (gas token, block explorer links in the impact report) may need adjusting
- [x] Update any hardcoded "Ethereum Mainnet" references in the sandbox UI/test dApp to reflect X Layer instead

**Correction (2026-07-14):** the checks above were apparently confirmed against a state that didn't survive — found and fixed a real, concrete break: `Sandbox.jsx` had the decoy wallet, mock token, and drainer contract addresses **hardcoded** from a one-off manual test earlier in this project's history. Those addresses only exist on one specific ephemeral fork instance; once the fork restarts (or `SANDBOX_DECOY_WALLET_PRIVATE_KEY` changes, as it did during the `.env` desync above), they silently point at nothing or the wrong thing — no error, just a broken/meaningless simulation. Fixed properly rather than re-hardcoding new values:

- `auth_server.py` now self-provisions on startup: checks whether the EVM fork is reachable, starts one if not (`sandbox/fork/start-evm-fork.sh`), deploys fresh mock contracts against it, and serves the real, current addresses via a new `GET /api/sandbox/config` endpoint.
- `Sandbox.jsx` fetches that config instead of hardcoding anything, with a loading/error state on the submit button rather than silently using stale values.
- Second related bug found the same way: `exploit-intel/corpus/drainer_addresses.json`'s "known drainer" entry was also stale (a different old address), silently making the demo's "known drainer" detection report `false` instead of erroring. `sandbox/deploy_contracts.py` now re-syncs that entry on every fresh deploy (`drainer_registry.resync_sandbox_test_drainer()`).
- Verified end-to-end with a real login + real `/api/simulate` call after both fixes: addresses match live, `known_drainer: true` correctly fires for the demo scenario.

---

### Phase 4 — Manual Verification (do this yourself, not another self-report)

- [ ] Personally connect OKX Wallet end-to-end, confirm session persists across a page reload
- [ ] Personally watch one full continuous Interactive Live Sandbox session on the X Layer fork — detect → connect → intercept → resolve
- [ ] Run the full intended demo flow (scan → verdict → popup → sandbox → impact report → attestation) 2–3 times yourself before recording anything

---

### Phase 5 — Full Pipeline Validation

- [x] Built real `GroqProvider`/`GeminiProvider` classes in `consensus/providers.py` (Groq primary, Gemini/Anthropic fallback, de-duplicated so one key never gets asked the same question 3x under different slot names) — see `attestation/README.md` "Re-run with real consensus"
- [~] Run against 10+ real deployed contracts on X Layer + general EVM, mix of clean and known-exploited — ran 8 real Ethereum mainnet contracts + 6 fixtures (14 total, existing Phase 7 infra). **X Layer side not done**: OKLink's contract-source API needs an API key we don't have, and the explorer UI is a JS-rendered SPA unscrapable via WebFetch — both confirmed directly, not assumed. Found real X Layer mainnet token addresses via OKX's own `xlayer-tokenlist` GitHub repo but not their verified source. Recommended proceeding on general EVM only rather than reconstruct-and-guess at source for integrity reasons; get an OKLink API key to unblock the X Layer side for real.
- [x] Check false-positive rate on the consensus engine (Groq primary, Gemini/Anthropic fallback) — 7/11 false positive rate on real clean contracts with real Groq inference live (Gemini/Anthropic slots still mock, no keys yet). Root-caused via a direct re-run with full per-model output, not just inferred: the two still-mock panel slots are deterministically identical (same heuristic, same input), so they always agree with each other, and the fail-closed "escalate to most severe" policy gets dragged toward their crude severity-count heuristic even in cases where Groq's real answer was more accurate (confirmed with a quoted example — Aave's proxy contract, where Groq correctly reasoned about the immutable admin mitigating the upgrade risk and the mocks didn't). Actionable implication: adding `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` is likely to reduce false positives more than anything else at this point.
- [x] Time full pipeline latency end-to-end for pay-per-call acceptability — min=7.2s max=54.8s avg=17.0s across 14 real runs (static analysis ~2.2s avg, consensus ~8.2s avg/44.7s max — Groq's real latency now, not mock's ~0s, attestation ~6.6s avg). Two real breakages found and fixed in the process (see below), not just latency measurement.
- [x] Fix any breakage found before moving to submission — two real bugs fixed: (1) `GROQ_MODEL=`/`GEMINI_MODEL=` present-but-empty in `.env` silently resolved to `""` instead of the hardcoded default (`os.environ.get(key, default)` only falls back on a missing key, not an empty one); (2) `consensus/providers.py` didn't load `.env` on its own, so `get_default_providers()` silently fell back to all-mock when imported outside the full pipeline chain. Both fixed in `consensus/providers.py`.

---

### Phase 6 — MCP Server, Deployment & Payment

- [ ] Deploy MCP server + auth gateway to an always-on host (not localhost) — **artifacts ready, not deployed** (per your call: prepare only, no hosting account/credentials involved). `Dockerfile` + `docker-compose.yml` (root) build and run all 3 backend services (`auth_server.py`, `facilitator.py`, `server.py`) plus an `anvil` EVM-fork sidecar; `requirements.txt` dry-run-verified to actually resolve (all packages installable). Added a `/health` endpoint to `auth_server.py` (didn't have one). Docker itself isn't available in this dev environment, so the build is reviewed carefully but not build-tested — see `DEPLOYMENT.md` for options.

  **Given no budget for hosting**, verified current (2026) pricing rather than assumed: Fly.io removed its free tier in 2024 (trial only, then paid), Railway's "free" tier is $1/month credit and explicitly not for always-on use. **Oracle Cloud's Always Free tier is the one real $0-forever option** — 2 ARM OCPU + 12GB RAM, no expiration — added as "Option 0" in `DEPLOYMENT.md` with the actual signup/setup steps. Flagged honestly: needs a card on file for identity verification (not charged on free resources), ARM64 capacity in popular regions is sometimes exhausted, Oracle can reclaim idle instances, and `solc`'s ARM64 Linux binary availability per-version hasn't been verified (x86_64 is what's been checked here) — confirm `solc-select install 0.8.20` actually works on the instance before assuming the rest of the build does.
- [ ] Set up basic uptime monitoring/alerting — **documented, no account created** (per your call). See `DEPLOYMENT.md`'s "Uptime monitoring" section: which endpoint to point a monitor at (`/health` on whichever host runs `auth_server.py` — that's the one that matters, it's what's actually live), and free-tier service options (UptimeRobot, Better Uptime).
- [x] Confirm final pay-per-call pricing, wire to real `/api/pricing` values
- [x] Run one real end-to-end paid call through the x402 facilitator + test payer wallet on X Layer testnet, using the now-deployed tUSDC as `PAYMENT_TOKEN_ADDRESS`
- [x] Add rate limiting/abuse protection on the MCP endpoint — `mcp-server/rate_limit_http.py`, wired into every live endpoint in `auth_server.py` (the backend the frontend actually calls): IP-keyed for pre-auth `/api/auth/nonce`+`/api/auth/login` (10/60s), wallet-keyed for the expensive `/api/audit`+`/api/simulate` (10/60s — real compute + a real on-chain attestation write per call), wallet-keyed and more generous for `/api/api-keys`+`/api/usage` (60/60s). Verified live: hammered the nonce endpoint past its limit and got real `429`s back through an actual HTTP request, not just a unit test; separately confirmed per-wallet buckets are isolated (one wallet's calls don't rate-limit a different wallet). Note: this is separate from the rate limiting already built into `mcp-server/server.py` (the standalone x402/MCP-protocol server) — that one protects a different, not-yet-deployed server; this one protects what's actually live today.

---

### Phase 7 — Disclaimer & Listing Submission

- [x] Draft disclaimer/liability language (verdicts are risk signals, not guarantees) — tool output, README, site footer
- [ ] Submit ASP for listing review at `okx.ai/tutorial/asp` — as early as possible
- [x] Prepare listing description covering both tools (Verdict Engine + Sandbox)
- [ ] Confirm listing is live before submitting the form

---

### Phase 8 — Demo & Social

- [ ] Script ≤90s demo: connect OKX Wallet → scan a risky contract → verdict resolves → popup appears → click into sandbox → watch wallet impact happen on X Layer → attestation shown
- [ ] Record from a session you've personally verified works (Phase 4)
- [ ] Post to X: what Vetra does, problems solved, tag `#okxai`, link demo

---

### Phase 9 — Form Submission (buffer day)

- [ ] Submit Google form (`forms.gle/mddEUagmDbyV37ws8`) before Jul 17 00:00 UTC
- [ ] Include ASP details + link to X post
- [ ] Double-check listing is still live/approved at submission time

---

### Parked / Not in Scope

- Solana support
- Full GitHub repo scanning (UI shows "coming soon" only)
- Email/password auth (wallet sign-in only)
- Further hardening of the Interactive Live Sandbox against real adversarial sites — "in hardening" framing stays in the pitch
