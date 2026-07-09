"""
Payload decoding (Phase 5) — "decode first, simulate second" for the
malicious-link use case: a phishing site asks the wallet to sign a raw
transaction/calldata blob without showing what it actually does. This
decodes that blob into a human-readable method + args *before* simulate.py
runs it against the fork, using the public 4byte/openchain.xyz signature
database for unknown selectors (via `cast 4byte-decode`).

Explicitly Layer 1: this decodes and simulates a payload that's already in
hand. It does not visit or crawl the originating site — that's the
(unbuilt) Layer 2 stretch goal.
"""
import re
import subprocess


class DecodeError(Exception):
    pass


def decode_calldata(calldata: str, decoded_from: str = None) -> dict:
    """Returns {"method": "fn(types)", "args": [...], "decoded_from": ...}."""
    result = subprocess.run(["cast", "4byte-decode", calldata], capture_output=True, text=True)
    if result.returncode != 0:
        raise DecodeError(f"could not decode calldata: {result.stderr}")

    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if not lines:
        raise DecodeError(f"no signature match found for selector {calldata[:10]}")

    # First line is `1) "fn(types)"` (possibly with alternates below it if
    # the selector collides — take the first, most-likely match).
    method_match = re.search(r'"([^"]+)"', lines[0])
    if not method_match:
        raise DecodeError(f"unexpected cast 4byte-decode output: {lines[0]}")
    method = method_match.group(1)
    args = [line.split(" [")[0].strip() for line in lines[1:]]

    return {"method": method, "args": args, "decoded_from": decoded_from}
