"""Tiny zero-dependency .env loader, shared by attestation scripts so they
work whether or not the caller has already `source .env`'d their shell."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def load_env():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


load_env()
