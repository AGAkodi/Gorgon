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

Wired into a long-running service via the MCP server (Phase 6) —
`mcp-server/server.py` calls this through `attestation/full_pipeline.py`.

`analyze(source_path, cwd=None)` — the optional `cwd` (added in Phase 7)
points solc at a multi-file project's own root so package-style imports
(`@uniswap/v3-core/...`) resolve correctly; only needed for real-world
multi-file contracts, not single-file fixtures. See
`evm/scripts/fetch_real_contract.py` (pulls verified source from Sourcify,
no API key needed) and `evm/real_contracts/` (gitignored — regenerate
rather than commit fetched third-party source) for how Phase 7's real-
contract validation set was built; full writeup of that pass, including
the false-positive-rate finding, is in `attestation/README.md`.
