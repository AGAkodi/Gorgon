# static-analysis

EVM static analyzer, normalized into the shared `static_findings` shape
defined in `schemas/verdict.schema.json`. Solana is out of scope for now
(the schema keeps `chain: "solana"` valid for later; see `TODO.md` Phase 1).

## EVM (done)

`evm/analyze.py` wraps Slither:

```sh
pip3 install -r static-analysis/evm/requirements.txt
python3 static-analysis/evm/analyze.py static-analysis/evm/fixtures/Reentrancy.sol
```

Requires `solc` on PATH (via `solc-select install <version> && solc-select use <version>`).

Validated against three known-vulnerable fixtures in `evm/fixtures/`:

- `Reentrancy.sol` → `reentrancy-eth` (high)
- `UncheckedCall.sol` → `unchecked-lowlevel` (medium), `arbitrary-send-eth` (high)
- `AccessControl.sol` → `arbitrary-send-eth` (high) — Slither doesn't have a
  generic "missing onlyOwner" detector, but it correctly flags the
  attacker-reachable consequence (withdraw() can send to a caller-controlled
  address after setOwner() is called with no access control). Catching the
  literal "no modifier on this function" pattern is exactly what Phase 2's
  multi-model consensus is for — static analysis and LLM review are meant to
  be complementary here, not redundant.

Unverified/bytecode-only input is handled explicitly: `analyze()` returns
`{"static_findings": [], "insufficient_data": true}` instead of crashing or
guessing.

Not yet done: wiring this into a long-running callable service (vs. a CLI
script) — that naturally lands with Phase 6's MCP server work.
