# Vetra — Remaining TODO (post database wiring)

**OKX.AI ASP Hackathon · Deadline: Jul 17, 2026 00:00 UTC**

Assumes Supabase + backend wiring is complete. This picks up from there:
a sanity check on the wiring claims, wallet connect (OKX Wallet, X Layer),
the sandbox wallet, then the remaining path to submission.

---

### Confirmed Done (independently verified on-chain)

- [x] VetraAttestation contract deployed to X Layer testnet — `0x7861C11Db0d154721f1D9D2E36A00A8f6aF68F30`, deploy tx Accepted on L2, confirmed directly on OKLink explorer (status, gas used, creator/contract addresses all matched)
- [x] `ATTESTATION_CONTRACT_ADDRESS` set in `.env`
- [x] Mock payment token (tUSDC) deployed to X Layer testnet, deploy tx Accepted on L2, confirmed directly on OKLink explorer
- [x] `PAYMENT_TOKEN_ADDRESS` set in `.env`
- [x] X Layer testnet chain ID confirmed as 1952 (via raw `eth_chainId` RPC call, cross-checked against ChainList — chain 195 confirmed deprecated/legacy, unrelated to current testnet)

---

### Immediate Next Check — Attestation Wired Into Live Pipeline

Deployment is confirmed, but whether the verdict pipeline actually CALLS
this contract on a real scan hasn't been checked yet. Do this before
anything else below.

- [x] Run a real `get_security_verdict` scan, get the `attestation.tx_hash` from the response
- [x] Confirm it is NOT all zeros this time
- [x] Take that tx hash and look it up yourself on the X Layer testnet explorer (`oklink.com/x-layer-testnet/tx/<hash>`) — confirm Accepted on L2 and that To matches `0x7861C11Db0d154721f1D9D2E36A00A8f6aF68F30`
- [x] Scan the SAME contract a second time — confirm cache hit reuses the SAME tx hash rather than writing a new one

---

### Phase 1 — Sanity Check Before Building Further

Two questions from the wiring review were never directly answered. Confirm
these now — if either is wrong, everything downstream (RLS-gated pages,
per-wallet API keys) is silently broken, not working.

- [ ] Confirm directly: is the custom JWT signed with Supabase's project JWT secret, or registered as a Third-Party Auth provider — so `auth.jwt()` can actually parse `wallet_address`?
- [ ] Confirm directly: does the frontend call Supabase directly with an in-memory JWT, or does every Supabase call proxy through the FastAPI backend using the httpOnly cookie?
- [ ] Sign in with two different wallets, two separate sessions — confirm Wallet B's API Keys page shows ZERO of Wallet A's keys (real screenshot/trace, not a description)
- [x] Scan the same contract twice — confirm second call shows "Cache Hit" badge, $0 cost (confirmed earlier; re-confirm attestation tx hash reuse now that attestation is live — see "Immediate Next Check" above)

---

### Phase 2 — Real Wallet Connect (replaces placeholder auth trigger)

- [ ] Wire "Get Started" (and any other entry point) to open the OKX Wallet connect prompt directly — not a generic WalletConnect modal, OKX Wallet as primary/first option
- [ ] On connect: request account access, confirm the app is targeting X Layer (chain ID check — prompt a network switch if the connected wallet is on the wrong chain)
- [ ] Feed the connected address into the existing SIWE nonce → sign → login flow already built
- [ ] Post-connect: nav updates to show truncated wallet address pill (e.g. `0x4a2f…c91e`), replacing "Get Started"
- [ ] Add a disconnect option from that same nav pill
- [ ] Confirm this is visually and functionally distinct from the Sandbox wallet (Phase 3) — different label, different color, never in the same UI region

---

### Phase 3 — Sandbox Wallet on X Layer

- [ ] Confirm the sandbox decoy wallet (`SANDBOX_DECOY_WALLET_PRIVATE_KEY`) is wired to operate against an X Layer fork, not just a generic EVM/Ethereum mainnet fork — since X Layer is the primary target chain now that Solana's dropped
- [ ] Label it explicitly "Sandbox Wallet (Simulated)" with a persistent "SIMULATED" tag, per the earlier UI spec — confirm it never says "Connect Wallet" anywhere
- [ ] Confirm mock balances are minted correctly on the X Layer fork for the decoy wallet (native token + relevant test tokens for whatever contract is being simulated)
- [ ] Re-confirm interception (`eth_sendTransaction`, `personal_sign`, `eth_signTypedData`) still resolves correctly now that it's pointed at an X Layer fork instead of a general EVM fork — chain-specific quirks (gas token, block explorer links in the impact report) may need adjusting
- [ ] Update any hardcoded "Ethereum Mainnet" references in the sandbox UI/test dApp to reflect X Layer instead

---

### Phase 4 — Manual Verification (do this yourself, not another self-report)

- [ ] Personally connect OKX Wallet end-to-end, confirm session persists across a page reload
- [ ] Personally watch one full continuous Interactive Live Sandbox session on the X Layer fork — detect → connect → intercept → resolve
- [ ] Run the full intended demo flow (scan → verdict → popup → sandbox → impact report → attestation) 2–3 times yourself before recording anything

---

### Phase 5 — Full Pipeline Validation

- [ ] Run against 10+ real deployed contracts on X Layer + general EVM, mix of clean and known-exploited
- [ ] Check false-positive rate on the consensus engine (Groq primary, Gemini/Anthropic fallback)
- [ ] Time full pipeline latency end-to-end for pay-per-call acceptability
- [ ] Fix any breakage found before moving to submission

---

### Phase 6 — MCP Server, Deployment & Payment

- [ ] Deploy MCP server + auth gateway to an always-on host (not localhost)
- [ ] Set up basic uptime monitoring/alerting
- [ ] Confirm final pay-per-call pricing, wire to real `/api/pricing` values
- [ ] Run one real end-to-end paid call through the x402 facilitator + test payer wallet on X Layer testnet, using the now-deployed tUSDC as `PAYMENT_TOKEN_ADDRESS`
- [ ] Add rate limiting/abuse protection on the MCP endpoint

---

### Phase 7 — Disclaimer & Listing Submission

- [ ] Draft disclaimer/liability language (verdicts are risk signals, not guarantees) — tool output, README, site footer
- [ ] Submit ASP for listing review at `okx.ai/tutorial/asp` — as early as possible
- [ ] Prepare listing description covering both tools (Verdict Engine + Sandbox)
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

- [ ] Solana support
- [ ] Full GitHub repo scanning (UI shows "coming soon" only)
- [ ] Email/password auth (wallet sign-in only)
- [ ] Further hardening of the Interactive Live Sandbox against real adversarial sites — "in hardening" framing stays in the pitch
