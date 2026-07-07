#!/usr/bin/env bash
# Starts a local EVM mainnet fork for transaction simulation (Phase 5).
# Requires Foundry (anvil) — https://getfoundry.sh
set -euo pipefail

cd "$(dirname "$0")/../.."
set -a
[ -f .env ] && source .env
set +a

RPC_URL="${EVM_MAINNET_FORK_RPC_URL:-https://ethereum-rpc.publicnode.com}"
PORT="${EVM_FORK_PORT:-8555}"

echo "Forking $RPC_URL on port $PORT..."
exec anvil --fork-url "$RPC_URL" --port "$PORT"
