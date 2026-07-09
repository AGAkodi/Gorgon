"""
Full verdict pipeline (Phase 4): wires static analysis (Phase 1) + multi-
model consensus (Phase 2) + exploit intelligence matching (Phase 3) +
on-chain attestation (Phase 4) into a single call that produces exactly the
shape locked in schemas/verdict.schema.json — Phase 0's schema, closed.

Caching: hash(chain+address+source) -> skip re-analysis entirely (including
the on-chain write) if unchanged, serve the cached result.
"""
import re
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "static-analysis" / "evm"))
sys.path.insert(0, str(REPO_ROOT / "consensus"))
sys.path.insert(0, str(REPO_ROOT / "exploit-intel"))
sys.path.insert(0, str(Path(__file__).parent))

from analyze import analyze  # noqa: E402
from engine import run_consensus  # noqa: E402
from providers import AnalysisContext  # noqa: E402
from similarity import match as exploit_match  # noqa: E402
from pipeline import attest  # noqa: E402
from cache import cache_key, get_cached, set_cached  # noqa: E402


def _extract_function_signatures(source: str) -> list:
    return re.findall(r"function\s+(\w+)\s*\(", source)


def run_verdict_pipeline(chain: str, address: str, source_code: str, use_cache: bool = True) -> dict:
    key = cache_key(chain, address, source_code)

    if use_cache:
        cached = get_cached(key)
        if cached is not None:
            return {**cached, "cache_hit": True}

    with tempfile.NamedTemporaryFile(suffix=".sol", mode="w", delete=False) as f:
        f.write(source_code)
        tmp_path = f.name
    try:
        static_result = analyze(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    static_findings = static_result["static_findings"]

    ctx = AnalysisContext(chain=chain, address=address, source_code=source_code, static_findings=static_findings)
    consensus_result = run_consensus(ctx)

    function_signatures = _extract_function_signatures(source_code)
    exploit_matches = exploit_match(static_findings, function_signatures)

    attestation = attest(chain, address, consensus_result["verdict"], int(time.time()))

    verdict = {
        "chain": chain,
        "address": address,
        "verdict": consensus_result["verdict"],
        "confidence": consensus_result["confidence"],
        "model_consensus": consensus_result["model_consensus"],
        "static_findings": static_findings,
        "exploit_matches": exploit_matches,
        "attestation": attestation,
        "cache_hit": False,
    }

    if use_cache:
        set_cached(key, verdict)

    return verdict
