# consensus

Multi-model consensus engine. Runs 2-3 LLMs in parallel over contract
context + Phase 1 static findings, each producing `{risk_category,
rationale}`. Agreement raises confidence; disagreement is surfaced as a
signal rather than averaged away.

## How it's wired

- `prompt_template.py` — the structured prompt (contract source + static
  findings in, strict `{risk_category, rationale}` JSON out).
- `providers.py` — `AnthropicProvider` and `OpenAIProvider` call the real
  APIs; `MockProvider` is a deterministic stand-in used when no key is
  configured. `get_default_providers()` is the *only* place that decides
  real vs. mock, keyed off whether `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
  are set in `.env`. Fill those in and the engine calls real models with no
  other code changes.
- `engine.py` — runs all providers in parallel (`ThreadPoolExecutor`),
  computes the overall verdict, and logs disagreements.

### Consensus logic

- All models agree → verdict = that category, confidence = 1.0.
- Models disagree → verdict = the **most severe** category raised by any
  model (fail closed — never averaged into a false middle ground),
  confidence dampened (`agreement_ratio * 0.7`), and the full breakdown
  appended to `consensus/data/disagreements.jsonl` for Phase 9's corpus
  growth loop.

## Validated (mock providers — no API keys yet)

`python3 consensus/test_consensus.py` runs all 6 fixtures from
`static-analysis/evm/fixtures/` through Phase 1 + Phase 2 and checks the
result lands in the expected bucket. Currently 5/6 pass. The one "failure"
is informative, not a bug:

- **SafeVault.sol** (checks-effects-interactions done correctly) triggers a
  real disagreement: the mock `Claude` slot uses a deliberately naive
  "conservative" persona that flags any low-level external call regardless
  of ordering, while `GPT-4`/`Consensus-3` correctly recognize the safe
  pattern. Fail-closed policy resolves this to `high_risk` — a false
  positive against the hand-labeled "good" bucket, logged to
  `disagreements.jsonl` exactly as Phase 2 asks for ("check for false
  positives/negatives").

This is the intended tradeoff: a security tool that silently averages away
a real disagreement is worse than one that occasionally over-flags a safe
contract for a second look. The mock's "conservative" persona is
deliberately unsophisticated to produce a believable disagreement case for
testing — once real API keys are added, actual models are expected to
reason about ordering correctly and this specific false positive should
disappear. Re-run `test_consensus.py` after adding keys to confirm.

Not yet done: live verification against real Claude/GPT calls (blocked on
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `.env`), and Solana-side testing
(out of scope for now, see `TODO.md`).
