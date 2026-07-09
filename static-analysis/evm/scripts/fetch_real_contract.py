#!/usr/bin/env python3
"""
Fetches verified source code for a real deployed mainnet contract from
Sourcify (public, no API key needed — unlike Etherscan's v2 API, which now
requires one). Writes the full file tree to real_contracts/<slug>/ so
multi-file imports (e.g. "@aave/core-v3/...") resolve the same way they did
when Sourcify verified them.

Usage: python3 fetch_real_contract.py <address> <slug> [--chain-id 1]
"""
import argparse
import json
import sys
from pathlib import Path

import requests

REAL_CONTRACTS_DIR = Path(__file__).parent.parent / "real_contracts"


def fetch(address: str, chain_id: int = 1) -> dict:
    url = f"https://sourcify.dev/server/v2/contract/{chain_id}/{address}?fields=sources,compilation"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save(address: str, slug: str, chain_id: int = 1) -> dict:
    data = fetch(address, chain_id)
    if data.get("match") is None:
        raise RuntimeError(f"{address}: no Sourcify match (not verified there)")

    out_dir = REAL_CONTRACTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    for relpath, info in data["sources"].items():
        file_path = out_dir / relpath
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(info["content"])

    compilation = data["compilation"]
    metadata = {
        "address": address,
        "chain_id": chain_id,
        "name": compilation.get("name"),
        "compiler_version": compilation.get("compilerVersion"),
        "fully_qualified_name": compilation.get("fullyQualifiedName"),
        "source": "sourcify",
    }
    (out_dir / "_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address")
    parser.add_argument("slug")
    parser.add_argument("--chain-id", type=int, default=1)
    args = parser.parse_args()

    metadata = save(args.address, args.slug, args.chain_id)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
