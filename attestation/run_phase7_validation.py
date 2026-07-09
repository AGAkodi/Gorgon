#!/usr/bin/env python3
"""
Phase 7 — Validation Pass: runs the full pipeline (static analysis ->
consensus -> exploit match -> attestation) against real deployed mainnet
contracts (fetched via Sourcify) plus the existing Phase 1/2 fixtures,
measuring per-stage latency and checking the false-positive/negative rate.

Real-contract sourcing note: precisely tracking down "the exact historic
vulnerable contract, with a compiler-compatible source" for enough famous
incidents turned into a research rabbit hole (see README) — no macOS solc
binaries exist for versions <0.7.6 at all (confirmed directly, not
assumed), which rules out most 2016-2020 era contracts (WETH9, DAI, The
DAO, Compound, Cream, Uniswap V2, etc. all predate 0.7.x). So the real-
contract set below is 8 real, clean, legitimate, Sourcify-verified mainnet
contracts (2020+, Solidity 0.7.6-0.8.20) — the harder and more important
test per the TODO's own framing ("a security tool that cries wolf
constantly is worse than useless"). The "known-bad" side reuses the
existing Phase 1/2 fixtures, which represent real, common vulnerability
classes without the compiler-fragmentation problem.

Usage: python3 attestation/run_phase7_validation.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "static-analysis" / "evm"))
sys.path.insert(0, str(REPO_ROOT / "consensus"))
sys.path.insert(0, str(REPO_ROOT / "exploit-intel"))
sys.path.insert(0, str(Path(__file__).parent))

from analyze import analyze  # noqa: E402
from engine import run_consensus, SEVERITY_ORDER  # noqa: E402
from providers import AnalysisContext, get_default_providers  # noqa: E402
from similarity import match as exploit_match  # noqa: E402
from pipeline import attest  # noqa: E402

REAL_CONTRACTS_DIR = REPO_ROOT / "static-analysis" / "evm" / "real_contracts"
FIXTURES_DIR = REPO_ROOT / "static-analysis" / "evm" / "fixtures"

# (slug, entry file relative to real_contracts/<slug>/, solc version, address, expected bucket)
REAL_CONTRACTS = [
    ("uniswap_v3_factory", "contracts/UniswapV3Factory.sol", "0.7.6",
     "0x1F98431c8aD98523631AE4a59f267346ea31F984", "good"),
    ("uniswap_v3_swaprouter", "contracts/SwapRouter.sol", "0.7.6",
     "0xE592427A0AEce92De3Edee1F18E0157C05861564", "good"),
    ("uniswap_v3_swaprouter02", "contracts/SwapRouter02.sol", "0.7.6",
     "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", "good"),
    ("uniswap_v3_position_manager", "contracts/NonfungiblePositionManager.sol", "0.7.6",
     "0xC36442b4a4522E871399CD717aBDD847Ab11FE88", "good"),
    ("aave_v3_pool_proxy",
     "@aave/core-v3/contracts/protocol/libraries/aave-upgradeability/InitializableImmutableAdminUpgradeabilityProxy.sol",
     "0.8.10", "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2", "good"),
    ("seaport_1_4", "contracts/Seaport.sol", "0.8.17",
     "0x00000000000001ad428e4906ae43d8f9852d0dd6", "good"),
    ("uniswap_universal_router", "contracts/UniversalRouter.sol", "0.8.17",
     "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b", "good"),
    ("euler_eusdc_proxy", "Proxy.sol", "0.8.20",
     "0xeb91861f8a4e1c12333f42dce8fb0ecdc28da716", "good"),
]

FIXTURES = [
    ("Reentrancy.sol", "0xFixtureReentrancy000000000000000001", "bad"),
    ("UncheckedCall.sol", "0xFixtureUncheckedCall00000000000001", "bad"),
    ("AccessControl.sol", "0xFixtureAccessControl000000000001", "bad"),
    ("SafeVault.sol", "0xFixtureSafeVault0000000000000001", "good"),
    ("SafeAccessControl.sol", "0xFixtureSafeAccessControl00001", "good"),
    ("SafeToken.sol", "0xFixtureSafeToken000000000000001", "good"),
]

_current_solc_version = None


def _use_solc(version: str):
    global _current_solc_version
    if version == _current_solc_version:
        return
    subprocess.run(["solc-select", "use", version], capture_output=True, text=True, check=True)
    _current_solc_version = version


def bucket_of(verdict: str) -> str:
    return "bad" if SEVERITY_ORDER[verdict] >= SEVERITY_ORDER["high_risk"] else "good"


def run_one(name: str, chain: str, address: str, entry_path: str, solc_version: str, expected: str,
            project_root: str = None) -> dict:
    _use_solc(solc_version)
    source_text = Path(entry_path).read_text()

    t0 = time.time()
    static_result = analyze(entry_path, cwd=project_root)
    t_static = time.time() - t0
    static_findings = static_result["static_findings"]

    t0 = time.time()
    providers = get_default_providers()
    ctx = AnalysisContext(chain=chain, address=address, source_code=source_text, static_findings=static_findings)
    consensus_result = run_consensus(ctx, providers=providers)
    t_consensus = time.time() - t0

    t0 = time.time()
    function_sigs = []  # not extracted for real multi-file contracts; consensus already has full source
    exploit_matches = exploit_match(static_findings, function_sigs)
    t_exploit = time.time() - t0

    t0 = time.time()
    attestation = attest(chain, address, consensus_result["verdict"], int(time.time()))
    t_attest = time.time() - t0

    total = t_static + t_consensus + t_exploit + t_attest
    actual_bucket = bucket_of(consensus_result["verdict"])
    passed = actual_bucket == expected

    return {
        "name": name,
        "address": address,
        "expected": expected,
        "verdict": consensus_result["verdict"],
        "confidence": consensus_result["confidence"],
        "disagreement": consensus_result["disagreement"],
        "passed": passed,
        "static_findings_count": len(static_findings),
        "static_severity_max": max((f["severity"] for f in static_findings), default="none"),
        "exploit_matches_count": len(exploit_matches),
        "attestation_tx": attestation["tx_hash"],
        "timing": {
            "static_analysis": round(t_static, 2),
            "consensus": round(t_consensus, 2),
            "exploit_match": round(t_exploit, 3),
            "attestation": round(t_attest, 2),
            "total": round(total, 2),
        },
    }


def main():
    providers = get_default_providers()
    live = any(type(p).__name__ != "MockProvider" for p in providers)
    print(f"Consensus providers: {[p.name for p in providers]} ({'LIVE' if live else 'MOCK — add ANTHROPIC_API_KEY/OPENAI_API_KEY to .env for live models'})\n")

    results = []

    print("=== Real deployed mainnet contracts ===")
    for slug, entry_rel, solc_version, address, expected in REAL_CONTRACTS:
        project_root = str(REAL_CONTRACTS_DIR / slug)
        entry_path = str(REAL_CONTRACTS_DIR / slug / entry_rel)
        try:
            r = run_one(slug, "evm", address, entry_path, solc_version, expected, project_root=project_root)
        except Exception as e:
            print(f"[ERROR] {slug}: {e}")
            results.append({"name": slug, "expected": expected, "passed": False, "error": str(e)})
            continue
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {slug:32s} verdict={r['verdict']:10s} conf={r['confidence']:.2f} "
              f"static_findings={r['static_findings_count']:3d} (max={r['static_severity_max']:8s}) "
              f"total={r['timing']['total']:.1f}s")

    print("\n=== Existing fixtures (Phase 1/2 regression) ===")
    for filename, address, expected in FIXTURES:
        entry_path = str(FIXTURES_DIR / filename)
        try:
            r = run_one(filename, "evm", address, entry_path, "0.8.20", expected)
        except Exception as e:
            print(f"[ERROR] {filename}: {e}")
            results.append({"name": filename, "expected": expected, "passed": False, "error": str(e)})
            continue
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {filename:32s} verdict={r['verdict']:10s} conf={r['confidence']:.2f} "
              f"static_findings={r['static_findings_count']:3d} (max={r['static_severity_max']:8s}) "
              f"total={r['timing']['total']:.1f}s")

    passed = [r for r in results if r.get("passed")]
    failed = [r for r in results if not r.get("passed")]
    good_results = [r for r in results if r.get("expected") == "good"]
    false_positives = [r for r in good_results if not r.get("passed")]

    print("\n--- Summary ---")
    print(f"{len(passed)}/{len(results)} passed")
    print(f"False positive rate on real clean contracts: {len(false_positives)}/{len(good_results)}")
    if failed:
        print("Failed:", [(r["name"], r.get("verdict", r.get("error"))) for r in failed])

    timings = [r["timing"]["total"] for r in results if "timing" in r]
    if timings:
        print(f"\nLatency: min={min(timings):.1f}s max={max(timings):.1f}s avg={sum(timings)/len(timings):.1f}s")
        for stage in ("static_analysis", "consensus", "exploit_match", "attestation"):
            stage_times = [r["timing"][stage] for r in results if "timing" in r]
            print(f"  {stage:16s} avg={sum(stage_times)/len(stage_times):.2f}s max={max(stage_times):.2f}s")

    report_path = Path(__file__).parent / "data" / "phase7_validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
