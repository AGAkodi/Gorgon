#!/usr/bin/env bash
# Single-container startup for the Vetra website + API (Option 2).
#
# This is the human-facing deploy: the FastAPI auth gateway (SIWE login,
# API keys, usage, and the /api/audit + /api/simulate pipeline) which ALSO
# serves the built React frontend from the same origin. It is NOT required
# for the OKX A2MCP listing — that's the separate MCP endpoint
# (start_listing.sh). Deploy this whenever; it never gates submission.
#
# auth_server.py self-provisions its own EVM fork on startup (checks the fork
# is reachable, starts sandbox/fork/start-evm-fork.sh if not, deploys fresh
# mock contracts), so no separate fork process is needed here.
#
# Railway injects $PORT and expects the app to listen on it; auth_server
# reads AUTH_SERVER_PORT, so we bridge the two.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export AUTH_SERVER_PORT="${PORT:-${AUTH_SERVER_PORT:-4023}}"

echo "[start_web] starting auth gateway + SPA on :${AUTH_SERVER_PORT} ..."
exec python3 mcp-server/auth_server.py
