#!/usr/bin/env bash
# Single-container startup for the Vetra A2MCP listing endpoint.
#
# The OKX.AI A2MCP listing points agents at ONE public URL: this MCP server's
# SSE endpoint. That endpoint depends on two things that must NOT be public —
# the x402 facilitator (payment verify/settle) and an anvil EVM fork (for
# simulate_wallet_interaction). This script runs all three in one container,
# in dependency order, so the whole listing is a single Railway service with
# a single exposed port.
#
# Dependency order matters: the MCP server calls the facilitator during its
# startup (resource_server.initialize()), and the facilitator + fork must
# already be answering before it does — otherwise the MCP server crashes on
# boot with a ConnectionRefused. Hence the health-gated waits below rather
# than fixed sleeps.
#
# Ports: Railway (and most PaaS) inject $PORT and expect the app to listen on
# it. We bind the MCP server there and keep the facilitator/fork on fixed
# internal ports. Override any *_PORT var to run outside that convention.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export MCP_SERVER_PORT="${PORT:-${MCP_SERVER_PORT:-4021}}"
export FACILITATOR_PORT="${FACILITATOR_PORT:-4022}"
export EVM_FORK_PORT="${EVM_FORK_PORT:-8555}"
export FACILITATOR_URL="${FACILITATOR_URL:-http://127.0.0.1:${FACILITATOR_PORT}}"
export EVM_FORK_RPC_URL="${EVM_FORK_RPC_URL:-http://127.0.0.1:${EVM_FORK_PORT}}"

log() { echo "[start_listing] $*"; }

# --- 1. EVM fork (anvil, forking X Layer testnet) — internal ---
log "starting EVM fork on :${EVM_FORK_PORT} ..."
bash sandbox/fork/start-evm-fork.sh &
FORK_PID=$!
for _ in $(seq 1 60); do
  if cast block-number --rpc-url "$EVM_FORK_RPC_URL" >/dev/null 2>&1; then
    log "fork is up"; break
  fi
  if ! kill -0 "$FORK_PID" 2>/dev/null; then log "FATAL: fork died on startup"; exit 1; fi
  sleep 1
done

# --- 2. x402 facilitator (payment verify/settle) — internal ---
log "starting facilitator on :${FACILITATOR_PORT} ..."
python3 mcp-server/facilitator.py &
FAC_PID=$!
for _ in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:${FACILITATOR_PORT}/health" >/dev/null 2>&1; then
    log "facilitator is up"; break
  fi
  if ! kill -0 "$FAC_PID" 2>/dev/null; then log "FATAL: facilitator died on startup"; exit 1; fi
  sleep 1
done

# --- 3. MCP server (the public A2MCP endpoint) — foreground ---
# Runs in the foreground so the container's lifecycle follows it: if the MCP
# server exits, the container exits and the platform restarts it.
log "starting MCP server on :${MCP_SERVER_PORT} (public A2MCP endpoint) ..."
exec python3 mcp-server/server.py
