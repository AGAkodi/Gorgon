#!/usr/bin/env python3
"""
Phase 4 validation: runs the full static+consensus+exploit+attestation
pipeline against a real fixture, confirms an on-chain attestation is
written, then re-runs to confirm the cache skips re-analysis (including
skipping the on-chain write) for unchanged input, and re-runs once more
with modified source to confirm the cache correctly misses on a change.

Usage: python3 attestation/test_full_pipeline.py
"""
import time
from pathlib import Path

from full_pipeline import run_verdict_pipeline

FIXTURE = Path(__file__).parent.parent / "static-analysis" / "evm" / "fixtures" / "Reentrancy.sol"


def main():
    source = FIXTURE.read_text()
    address = "0xFullPipelineTest0000000000000000000001"

    print("=== run 1: cache miss, full pipeline + real on-chain attest ===")
    t0 = time.time()
    result1 = run_verdict_pipeline("evm", address, source)
    elapsed1 = time.time() - t0
    print(f"verdict={result1['verdict']} confidence={result1['confidence']} "
          f"cache_hit={result1['cache_hit']} tx={result1['attestation']['tx_hash']} "
          f"elapsed={elapsed1:.1f}s")
    assert result1["cache_hit"] is False
    assert result1["attestation"]["tx_hash"].startswith("0x")

    print("\n=== run 2: same input, expect cache hit (no new tx, fast) ===")
    t0 = time.time()
    result2 = run_verdict_pipeline("evm", address, source)
    elapsed2 = time.time() - t0
    print(f"verdict={result2['verdict']} cache_hit={result2['cache_hit']} "
          f"tx={result2['attestation']['tx_hash']} elapsed={elapsed2:.2f}s")
    assert result2["cache_hit"] is True
    assert result2["attestation"]["tx_hash"] == result1["attestation"]["tx_hash"], \
        "cache hit should serve the exact same attestation, not write a new one"
    assert elapsed2 < elapsed1 / 5, "cache hit should be drastically faster than a full run"

    print("\n=== run 3: modified source, expect cache MISS (new analysis + new tx) ===")
    modified_source = source + "\n// a trivial comment change to alter the source hash\n"
    t0 = time.time()
    result3 = run_verdict_pipeline("evm", address, modified_source)
    elapsed3 = time.time() - t0
    print(f"verdict={result3['verdict']} cache_hit={result3['cache_hit']} "
          f"tx={result3['attestation']['tx_hash']} elapsed={elapsed3:.1f}s")
    assert result3["cache_hit"] is False
    assert result3["attestation"]["tx_hash"] != result1["attestation"]["tx_hash"], \
        "changed source should produce a fresh attestation, not reuse the cached one"

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
