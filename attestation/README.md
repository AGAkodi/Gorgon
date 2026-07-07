# attestation

On-chain attestation contract (X Layer testnet): stores
`hash(chain+address+verdict+timestamp)` and emits an event so any agent can
query whether an address has been attested and what the verdict hash was.

Not yet implemented — see Phase 4 in `TODO.md`.
