#!/usr/bin/env python3
"""
Phase 2 validation: runs every fixture in static-analysis/evm/fixtures/
through Phase 1 (static analysis) + Phase 2 (consensus), and checks the
result lands in the expected bucket (known-bad shouldn't come back "safe",
known-good shouldn't come back "high_risk"/"critical").

Usage: python3 consensus/test_consensus.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "static-analysis" / "evm"))
sys.path.insert(0, str(Path(__file__).parent))

from analyze import analyze  # noqa: E402
from engine import run_consensus, SEVERITY_ORDER  # noqa: E402
from providers import AnalysisContext, get_default_providers  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "static-analysis" / "evm" / "fixtures"

# Known-bad: expected to land at high_risk or critical.
# Known-good: expected to land at safe or caution.
EXPECTED_BUCKET = {
    "Reentrancy.sol": "bad",
    "UncheckedCall.sol": "bad",
    "AccessControl.sol": "bad",
    "SafeVault.sol": "good",
    "SafeAccessControl.sol": "good",
    "SafeToken.sol": "good",
}


def bucket_of(verdict: str) -> str:
    return "bad" if SEVERITY_ORDER[verdict] >= SEVERITY_ORDER["high_risk"] else "good"


def main():
    providers = get_default_providers()
    print(f"Providers: {[p.name for p in providers]} "
          f"({'live' if any(type(p).__name__ != 'MockProvider' for p in providers) else 'mock — add API keys to .env for live models'})\n")

    results = []
    for filename, expected in EXPECTED_BUCKET.items():
        path = FIXTURES_DIR / filename
        static_result = analyze(str(path))
        ctx = AnalysisContext(
            chain="evm",
            address=filename,
            source_code=path.read_text(),
            static_findings=static_result["static_findings"],
        )
        consensus = run_consensus(ctx, providers=providers)
        actual = bucket_of(consensus["verdict"])
        passed = actual == expected
        results.append((filename, expected, consensus, passed))

        status = "PASS" if passed else "FAIL"
        flag = " [DISAGREEMENT]" if consensus["disagreement"] else ""
        print(f"[{status}] {filename:24s} expected={expected:5s} verdict={consensus['verdict']:10s} "
              f"confidence={consensus['confidence']}{flag}")
        for m in consensus["model_consensus"]:
            print(f"         - {m['model']:12s} {m['risk_category']:10s} {m['rationale']}")
        print()

    failed = [r for r in results if not r[3]]
    disagreements = [r for r in results if r[2]["disagreement"]]
    print("---")
    print(f"{len(results) - len(failed)}/{len(results)} passed. "
          f"{len(disagreements)} contract(s) produced model disagreement (logged to consensus/data/disagreements.jsonl).")
    if failed:
        print("FAILED:", [f[0] for f in failed])
        sys.exit(1)


if __name__ == "__main__":
    main()
