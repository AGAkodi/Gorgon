# attestation

On-chain attestation contract (X Layer testnet): stores a verdict hash and
emits an event so any agent can query whether an address has been attested
and what the verdict hash was.

## Deploy wallet (Phase 0 — done)

A throwaway dev keypair for testnet deploys was generated via `cast wallet new`
and is stored in `.env` (gitignored) as `ATTESTATION_WALLET_PRIVATE_KEY`. It
holds zero real value and is testnet-only.

- Address: `0x7Cd265c14862f659a55EEEfa25Ca5BdF626E908E`
- Funded with 0.2 testnet OKB, confirmed via `cast balance`
- RPC: `X_LAYER_TESTNET_RPC_URL` in `.env` (chain id 1952). Originally
  `xlayertestrpc.okx.com/terigon`; that endpoint went unreachable mid-session
  (DNS/connection timeouts across retries while general internet access was
  otherwise fine) so `.env` now points at the public `testrpc.xlayer.tech`,
  independently confirmed to be the same network (matching chain id and the
  wallet's balance). Swap back if/when the original is back up.

## Contract (Phase 4 — done)

`contract/VetraAttestation.sol` — minimal, owner-gated:

- `attest(chain, target, verdictHash)` — only the pipeline's wallet can
  write. Stores `{verdictHash, block.timestamp}` keyed by
  `keccak256(abi.encode(chain, target))`.
- `getAttestation(chain, target)` — public read, returns
  `(verdictHash, timestamp, exists)`.

`target` is `string`, not the native `address` type — Vetra attests
addresses on other chains too, including formats that aren't 20-byte EVM
addresses.

Note: the key derivation uses `abi.encode`, not `abi.encodePacked`. The
first draft used `encodePacked` on two dynamic strings — running Vetra's
own Phase 1 static analyzer against its own contract caught this
immediately (`encode-packed-collision`, SWC-133: two concatenated
variable-length strings can collide, e.g. `("ev","mFoo")` == `("evm","Foo")`).
Fixed before deploying; re-ran the analyzer to confirm clean.

**Deployed:** `0x835f9ab4f2187427189dd463c4126011d3ebdb48` on X Layer
testnet (chain id 1952). Verified on-chain (not via block explorer source
verification — no verifier API key set up for this yet): bytecode present
via `cast code`, `owner()` returns the deploy wallet, and a full
attest → getAttestation round trip confirmed both the write and the
negative case (unattested address returns `exists: false`).

## Pipeline wiring (Phase 4 — done)

- `pipeline.py` — `compute_verdict_hash()` (keccak256 over
  `abi.encode(chain, address, verdict, timestamp)`, via `cast abi-encode` +
  `cast keccak` — shells out to Foundry rather than adding a web3.py
  dependency), `attest()` (write path), `get_attestation()` (read path).
  `attest()`'s returned timestamp is the actual mined block's timestamp
  (fetched via `cast block`), not the pre-submission value used to compute
  the hash, so it stays consistent with what `get_attestation()` reads back.
- `full_pipeline.py` — `run_verdict_pipeline(chain, address, source)` wires
  Phase 1 (static analysis) → Phase 2 (consensus) → Phase 3 (exploit match)
  → Phase 4 (attest), producing exactly the shape locked in
  `schemas/verdict.schema.json`.
- `cache.py` — `hash(chain+address+source)` → if unchanged, skip
  re-analysis **and** the on-chain write entirely, serve the cached
  attestation. Cache lives at `attestation/data/cache.json` (gitignored —
  it's operational state, not corpus data).

Validated end-to-end via `python3 attestation/test_full_pipeline.py`
against a real fixture with real on-chain writes: first run does a full
analysis + attests on-chain; second run (same input) hits cache instantly
with zero new transactions, serving the identical `tx_hash`; third run
(modified source) correctly misses the cache and produces a fresh
attestation with a different `tx_hash`.

MCP server wiring (Phase 6) calls `run_verdict_pipeline()` from an agent
request — see `mcp-server/README.md`.

## Phase 7 — Validation Pass (done)

`run_phase7_validation.py` runs static analysis → consensus → exploit match
→ attestation against 8 real, deployed mainnet contracts (fetched from
Sourcify — no API key needed, unlike Etherscan's v2 API) plus the existing
Phase 1/2 fixtures, timing every stage.

**Real-contract sourcing constraint, confirmed directly:** no macOS solc
binaries exist in GitHub releases for versions below 0.7.6 — checked, not
assumed (Linux/Windows builds exist for old versions, macOS doesn't). That
rules out most 2016–2020-era contracts (WETH9, DAI, The DAO, Compound,
Cream, Uniswap V2 all predate 0.7.x) in this environment. So the real-
contract set is 8 clean, legitimate, Sourcify-verified 2020+ mainnet
contracts (Uniswap V3 Factory/SwapRouter/SwapRouter02/PositionManager,
Aave V3 Pool proxy, Seaport, Uniswap Universal Router, Euler eUSDC proxy) —
arguably the harder and more relevant test anyway, per the TODO's own
framing ("a security tool that cries wolf constantly is worse than
useless"): these are the contracts a false positive would actually hurt.
One (Universal Router) failed to compile — Sourcify's bundled source for
that specific contract is missing several of its dependencies
(`solmate`, `permit2`, `openzeppelin-contracts`); documented as a real,
encountered limitation of this sourcing method rather than worked around.

**A real pipeline bug found and fixed:** `analyze()` had no way to tell
solc where a multi-file project's package-style imports
(`@uniswap/v3-core/...`) should resolve from, so it silently used
whatever directory happened to be the caller's cwd. Added an optional
`cwd` parameter (`static-analysis/evm/analyze.py`), pointing it at each
contract's own fetched root — confirmed fixed against `SwapRouter.sol`,
which imports across package boundaries and failed before the fix.

**The key finding — false positive rate:** 6 of 7 successfully-analyzed
real contracts (86%) came back `high_risk`, all false positives. Root
cause, confirmed by inspection: the mock consensus's "conservative"
persona (Phase 2) flags the mere *presence* of certain rule names
(`low-level-calls`, `unchecked-lowlevel`, `calls-loop`) as `high_risk`
regardless of Slither's own assigned severity for that finding — and
low-level calls are ubiquitous in legitimate real-world code (proxy
patterns, raw ETH transfers, gas-optimized assembly). This is not a
pipeline bug — mock providers were explicitly built (Phase 2) to prove the
engineering works (parallel execution, consensus/disagreement logic), not
to make real security judgments, and this validation pass is exactly what
demonstrates *why* that distinction matters. **The one unambiguous
pre-submission action item this pass produced: real
`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` are required before this pipeline's
false-positive rate means anything.** Retuning the mock's heuristics to
score better here would just be overfitting the validation, not fixing the
actual problem — left as-is on purpose.

**Latency** (avg / max, mock providers): static analysis 3.2s / 17.0s
(the 17s outlier is Seaport, 731 findings across a large multi-file
project); consensus ~0.00s (mock — no network round trip; real LLM calls
will add several seconds each, run in parallel via `ThreadPoolExecutor` so
bounded by the slowest model, not the sum); exploit match ~0.003s; **on-
chain attestation 8.2s / 12.1s — the real bottleneck**, inherent to waiting
for testnet transaction confirmation. Total per call: 11.4s avg, 24.4s
max. With real consensus added, realistic total latency is likely
15–25s/call — worth weighing against the "pay-per-call, no negotiation"
promise (Phase 6); e.g. returning the result once static+consensus+exploit
match complete and recording the attestation as fire-and-forget afterward
would cut the user-facing wait roughly in half, if that tradeoff is
wanted.

Full per-contract results: `attestation/data/phase7_validation_report.json`
(gitignored, regenerate via `python3 attestation/run_phase7_validation.py`
— requires all 4 solc versions installed: 0.7.6, 0.8.10, 0.8.17, 0.8.20).
