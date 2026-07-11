"""
Analysis cache (Phase 4): hash(chain+address+bytecode) -> skip re-analysis
if unchanged, serve the cached attestation instead. Wired to Supabase verdict_cache.
"""
import hashlib
import json
import os
import requests
from pathlib import Path

CACHE_PATH = Path(__file__).parent / "data" / "cache.json"


def cache_key(chain: str, address: str, bytecode_or_source: str) -> str:
    return hashlib.sha256(f"{chain}:{address}:{bytecode_or_source}".encode()).hexdigest()


def _get_supabase_config():
    # If variables are not yet in os.environ, try loading via env helper
    if "NEXT_PUBLIC_SUPABASE_URL" not in os.environ:
        try:
            from env import load_env
            load_env()
        except Exception:
            pass
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    return url, service_key


def get_cached(key: str):
    url, service_key = _get_supabase_config()
    if url and service_key:
        try:
            headers = {
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}"
            }
            resp = requests.get(f"{url}/rest/v1/verdict_cache?contract_hash=eq.{key}", headers=headers)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    return rows[0]["verdict"]
        except Exception as e:
            print(f"Supabase cache read error (falling back): {e}")

    # Fallback to local file cache
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
            return data.get(key)
        except Exception:
            pass
    return None


def set_cached(key: str, verdict: dict) -> None:
    url, service_key = _get_supabase_config()
    if url and service_key:
        try:
            headers = {
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            payload = {
                "contract_hash": key,
                "chain": verdict.get("chain", "evm"),
                "verdict": verdict
            }
            resp = requests.post(f"{url}/rest/v1/verdict_cache", headers=headers, json=payload)
            if resp.status_code in (200, 201):
                return
            else:
                print(f"Supabase cache write status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Supabase cache write error: {e}")

    # Fallback/mirror to local file cache
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    data[key] = verdict
    try:
        CACHE_PATH.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

