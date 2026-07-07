#!/usr/bin/env bash
# Starts a local Solana validator for transaction simulation (Phase 5).
# Requires the Solana CLI — https://docs.solanalabs.com/cli/install
#
# Add `--clone <PUBKEY> --url "$SOLANA_RPC_URL"` per account/program once
# Phase 5 knows which mainnet accounts (e.g. known drainer/router contracts)
# need to be present in the simulated wallet-impact scenarios.
set -euo pipefail

cd "$(dirname "$0")/../.."
set -a
[ -f .env ] && source .env
set +a

LEDGER_DIR="${SOLANA_FORK_LEDGER_DIR:-/tmp/vetra-solana-ledger}"

echo "Starting local validator (ledger: $LEDGER_DIR)..."
exec solana-test-validator --ledger "$LEDGER_DIR" --reset
