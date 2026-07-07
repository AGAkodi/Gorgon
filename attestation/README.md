# attestation

On-chain attestation contract (X Layer testnet): stores
`hash(chain+address+verdict+timestamp)` and emits an event so any agent can
query whether an address has been attested and what the verdict hash was.

## Deploy wallet (Phase 0 — done)

A throwaway dev keypair for testnet deploys was generated via `cast wallet new`
and is stored in `.env` (gitignored) as `ATTESTATION_WALLET_PRIVATE_KEY`. It
holds zero real value and is testnet-only.

- Address: `0x7Cd265c14862f659a55EEEfa25Ca5BdF626E908E`
- Funded with 0.2 testnet OKB, confirmed via `cast balance`
- RPC: `X_LAYER_TESTNET_RPC_URL` in `.env` (chain id 1952), confirmed reachable via `cast chain-id`

The contract itself (store `hash(chain+address+verdict+timestamp)`, emit
event, deploy, read path) is not yet implemented — see Phase 4 in `TODO.md`.
