#!/usr/bin/env python3
"""
EVM static analysis service (Phase 1).

Wraps Slither and normalizes its detector output into the shared
`static_findings` shape defined in schemas/verdict.schema.json:

    {"rule": "", "severity": "", "location": ""}

Usage:
    python3 analyze.py path/to/Contract.sol
    python3 analyze.py path/to/Contract.sol --json   # raw JSON to stdout
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Slither/crytic-compile impact levels -> our schema's severity enum.
# "Optimization" findings are gas/style suggestions, not security findings,
# so they're dropped rather than mapped.
IMPACT_TO_SEVERITY = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Informational": "info",
}


def _location(elements: list) -> str:
    for el in elements:
        mapping = el.get("source_mapping", {})
        lines = mapping.get("lines", [])
        name = el.get("name", "")
        if lines:
            line_str = f"L{lines[0]}" if len(lines) == 1 else f"L{lines[0]}-{lines[-1]}"
            return f"{name}() {line_str}" if name else line_str
    return "unknown"


def normalize(slither_json: dict) -> list:
    findings = []
    for detector in slither_json.get("results", {}).get("detectors", []):
        impact = detector.get("impact")
        severity = IMPACT_TO_SEVERITY.get(impact)
        if severity is None:
            continue  # drop Optimization / unknown impact levels
        findings.append(
            {
                "rule": detector.get("check", "unknown"),
                "severity": severity,
                "location": _location(detector.get("elements", [])),
            }
        )
    return findings


def has_solidity_source(path: Path) -> bool:
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return False
    return "pragma solidity" in text or "contract " in text


def analyze(source_path: str, cwd: str = None) -> dict:
    """cwd: directory to run slither/solc from, so package-style imports
    (e.g. "@uniswap/v3-core/...") resolve against the contract's own
    project root rather than the caller's working directory. Only needed
    for multi-file real-world projects; single-file fixtures don't care."""
    path = Path(source_path)

    if not path.exists():
        raise FileNotFoundError(source_path)

    if not has_solidity_source(path):
        # Bytecode-only / unverified contract: explicit insufficient-data
        # result rather than pretending we ran static analysis on it.
        return {"static_findings": [], "insufficient_data": True}

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    Path(tmp_path).unlink()  # slither refuses to write over an existing file

    target = str(path.resolve()) if cwd else str(path)
    result = subprocess.run(
        ["slither", target, "--json", tmp_path],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    try:
        raw = json.loads(Path(tmp_path).read_text())
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        raise RuntimeError(
            f"slither did not produce valid JSON output. stderr:\n{result.stderr}"
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not raw.get("success", True):
        raise RuntimeError(f"slither run failed: {raw.get('error')}")

    return {"static_findings": normalize(raw), "insufficient_data": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Path to a .sol file")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    output = analyze(args.source)
    print(json.dumps(output, indent=2 if not args.json else None))


if __name__ == "__main__":
    sys.exit(main())
