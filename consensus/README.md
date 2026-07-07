# consensus

Multi-model consensus engine. Runs 2-3 LLMs in parallel over contract context
+ static findings, each producing `{risk_category, rationale}`. Agreement
raises confidence; disagreement is surfaced as a signal rather than averaged
away.

Not yet implemented — see Phase 2 in `TODO.md`.
