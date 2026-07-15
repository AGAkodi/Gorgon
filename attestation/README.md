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

## Re-run with real consensus (TODO.md Phase 5, 2026-07-13)

The validation above was mock-only. `consensus/providers.py` now has real
`GroqProvider`/`GeminiProvider` classes (Groq primary, Gemini/Anthropic
fallback per TODO.md), and a real `GROQ_API_KEY` landed in `.env` this
session — so this is the first run with genuine LLM inference in the
panel (Groq real; Gemini/Anthropic slots still mock, no keys for those yet).

**Result: 7/14 passed, false positive rate 7/11 on real clean contracts —
essentially unchanged from the mock-only run.** But the *reason* changed,
and that's the actual finding:

- **2 real failures, unrelated to model quality:** `seaport_1_4` hit
  Groq's rate limit outright (413 — Seaport's flattened multi-file source
  is 28,437 tokens, Groq's free/on-demand tier caps at 8,000 TPM).
  `uniswap_universal_router` still fails to compile (same pre-existing
  Sourcify-bundled-source-missing-dependencies issue documented above,
  nothing to do with consensus).
- **The false positives are not purely a mock-heuristic artifact anymore,
  but the mock personas are still doing most of the damage.** Two of the
  three panel slots (`Gemini`, `Consensus-3`) are still `MockProvider`
  instances running the *identical* deterministic "balanced" heuristic on
  the same static findings — meaning they always agree with each other,
  and the only independent voice is Groq. Confidence `0.47` on every
  failing case confirms this mechanically (exactly 2-of-3 agreement, per
  the consensus formula) — Groq is disagreeing with the mock pair every
  time.

  Directly re-ran `aave_v3_pool_proxy` (verified in isolation, not just
  inferred from the summary) to see who actually said what:

  ```text
  resolved verdict: high_risk  confidence: 0.47
    Groq         caution    "thin proxy relying on parent implementations that include
                             delegatecalls and upgrade functions; while the admin is
                             immutable, the initialize/upgrade pathways ... could be
                             misused if access control is insufficient, posing moderate risk"
    Gemini       high_risk  "A high-severity finding is present..." (mock, generic)
    Consensus-3  high_risk  "A high-severity finding is present..." (mock, generic)
  ```

  Groq's real answer here is the *better* one — it correctly reasons about
  the immutable admin mitigating the upgrade risk, something the mock's
  severity-count heuristic structurally cannot do. The fail-closed policy
  (escalate to the most severe of any disagreement) picked the mocks'
  cruder `high_risk` over Groq's more accurate `caution`. This is the
  disagreement-handling design working exactly as built (Phase 2) — it's
  correctly refusing to silently average away a real disagreement — but
  it means **the more mock voices are in the panel, the more the fail-
  closed policy gets dragged toward their crude heuristic**, even when the
  real model in the room is reasoning better.

- **The actionable implication:** adding `GEMINI_API_KEY` and/or
  `ANTHROPIC_API_KEY` is likely to reduce false positives more than
  tuning anything else, since it replaces the crude, context-blind mock
  voters with real judgment too — which is exactly what "Groq primary,
  Gemini/Anthropic fallback" was designed to do once more keys exist.

**Real bug fixed in the process:** `GROQ_MODEL=` / `GEMINI_MODEL=` (present
but empty in `.env`) were silently resolving to `""` instead of falling
back to their hardcoded defaults — `os.environ.get(key, default)`'s
default only applies when the key is *absent*, not when it's present but
empty. Fixed in `consensus/providers.py` (`model or os.environ.get(...) or
default`, not `model or os.environ.get(..., default)`). Also fixed:
`consensus/providers.py` didn't load `.env` on its own, so
`get_default_providers()` silently fell back to mock when imported
standalone rather than through the full pipeline — it now loads `.env`
itself, same as `attestation/pipeline.py` does.

Full report: `attestation/data/phase7_validation_report.json` (regenerate
via `python3 attestation/run_phase7_validation.py`).
