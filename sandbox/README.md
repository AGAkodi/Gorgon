# sandbox

Transaction simulation engine (Layer 1). Runs proposed calls or decoded
payloads against a decoy wallet on an EVM mainnet-fork (Anvil) or a forked
Solana local validator, producing the wallet impact report shape defined in
`schemas/simulation.schema.json`.

## Fork infra (Phase 0 — done)

Both local forks are validated and scripted:

```sh
./sandbox/fork/start-evm-fork.sh        # anvil, forks EVM_MAINNET_FORK_RPC_URL from .env
./sandbox/fork/start-solana-validator.sh  # solana-test-validator
```

- EVM fork defaults to the public `ethereum-rpc.publicnode.com` RPC (rate-limited
  but confirmed reachable). Swap in a Tenderly/Alchemy/Infura URL in `.env` for
  anything beyond local dev.
- Solana validator starts bare (no cloned accounts yet). Once Phase 5 picks the
  specific known-drainer/router contracts to simulate against, add
  `--clone <PUBKEY> --url "$SOLANA_RPC_URL"` per account to
  `start-solana-validator.sh`.

The actual simulation engine (decoy wallet funding, calldata construction,
wallet-impact-report generation) is not yet implemented — see Phase 5 in
`TODO.md`.
