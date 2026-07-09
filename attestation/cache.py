"""
Analysis cache (Phase 4): hash(chain+address+bytecode) -> skip re-analysis
if unchanged, serve the cached attestation instead. Local JSON file — same
lightweight-first approach as exploit-intel's TF-IDF index, no DB dependency
for a hackathon-scale cache.
"""
import hashlib
import json
from pathlib import Path

CACHE_PATH = Path(__file__).parent / "data" / "cache.json"


def cache_key(chain: str, address: str, bytecode_or_source: str) -> str:
    return hashlib.sha256(f"{chain}:{address}:{bytecode_or_source}".encode()).hexdigest()


def _load() -> dict:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text())


def get_cached(key: str):
    return _load().get(key)


def set_cached(key: str, verdict: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[key] = verdict
    CACHE_PATH.write_text(json.dumps(data, indent=2))
