# sandbox

Transaction simulation engine (Layer 1). Runs proposed calls or decoded
payloads against a decoy wallet on an EVM mainnet-fork (Anvil), producing
the wallet impact report shape defined in `schemas/simulation.schema.json`.

**Scope note (required by TODO.md Phase 5):** this simulates the
transaction's impact against a local fork. It does not visit, crawl, or
execute anything against a live external site — that's the (unbuilt,
would-need-hardening) Layer 2 stretch goal. Solana is out of scope for now,
same as earlier phases — the fork script exists (`start-solana-validator.sh`)
but the simulation engine below is EVM-only.

## Fork infra (Phase 0 — done)

```sh
./sandbox/fork/start-evm-fork.sh        # anvil, forks EVM_MAINNET_FORK_RPC_URL from .env
./sandbox/fork/start-solana-validator.sh  # solana-test-validator (unused by the engine below)
```

## Mock contracts (Phase 5 — done)

`contracts/MockERC20.sol` — minimal mintable ERC20, gives the decoy wallet a
mock balance on the fork (no real value, no mainnet storage-slot guessing
needed). `contracts/DrainerClaim.sol` — models a real "claim your airdrop"
drainer pattern: `claim(token)` calls `transferFrom(caller, attackerWallet,
balance)`, i.e. it only works because the victim was tricked into an
earlier unlimited `approve()`. Both were run through Vetra's own Phase 1
analyzer before use — `MockERC20` came back clean, `DrainerClaim` correctly
came back flagged high-severity (`unchecked-transfer`), as expected for a
fixture that's deliberately malicious.

`deploy_contracts.py` deploys both to a running fork, funds a dedicated
decoy wallet (`SANDBOX_DECOY_WALLET_PRIVATE_KEY` in `.env` — a throwaway
keypair, local-fork-only, never touches a real chain) with 10,000 mock
tokens and enough ETH for gas.

## Decode-first, simulate-second (Phase 5 — done)

`decode.py` — for the "malicious link" input mode (TODO's second accepted
input shape: a decoded payload rather than a direct call): given raw
calldata, decodes it into a method signature + args via
`cast 4byte-decode` (the public openchain.xyz signature database), *before*
simulating it. This is the step that would let a user/agent see "this
isn't a claim, it's an unlimited approval to X" before ever signing.

## Simulation engine (Phase 5 — done)

`simulate.py` — `simulate_call()` accepts either a structured
`(function_signature, args)` call or raw `calldata` (the decoded-payload
mode), impersonates the decoy wallet on the fork (`anvil_impersonateAccount`
— no private key needed, matching how Vetra would simulate for an
arbitrary real user's address in production), diffs ERC20 balances
before/after, and parses `Transfer`/`Approval`/`OwnershipTransferred` logs
(topic hashes independently recomputed via `cast keccak`, not trusted from
memory) into the wallet impact report shape.

Risk classification (`_risk_summary`) checks, in order: an approval granted
to a known drainer → critical; funds transferred out to a known drainer
address → critical; a balance outflow via a call to a known drainer
contract → critical; any other balance decrease → high_risk (a drain via a
*pre-existing* approval doesn't necessarily emit a fresh `Approval` event in
the same transaction, so this can't be gated on that — an earlier version
of this logic missed that and under-flagged a same-session drain to
`caution`, caught in testing below); ownership/permission changes →
high_risk; an unlimited approval to an unknown spender → caution; anything
else → safe.

`exploit-intel/drainer_registry.py` — the "cross-reference simulated
spender addresses against exploit corpus" piece. Honesty note: this is a
placeholder registry, not live threat intel — a websearch for real
documented drainer contract addresses (Inferno Drainer, Monkey Drainer,
etc.) turned up plenty of reporting but nothing with specific addresses
independently verifiable this session, so nothing unverifiable was added.
Seeded only with the sandbox's own deployed test drainer
(`source: "sandbox_test_seed"`), which is enough to prove the mechanism
works end-to-end. Real entries get appended via `register_drainer()`
(same append-only pattern as `exploit-intel/ingest.py`) as they're
confirmed — e.g. from Phase 9's flywheel.

## Validated

`python3 sandbox/test_simulate.py` (requires the fork running) models the
full attack end-to-end and validates every report against
`schemas/simulation.schema.json` with real JSON Schema validation
(`jsonschema.validate`, not just a manual key check):

- **Scenario A** (malicious-link flow): raw calldata decoded first →
  confirmed `approve(address,uint256)` with a near-max amount → spender
  registered as a known drainer → simulated → correctly reports an
  unlimited approval to a known drainer, verdict `critical`.
- **Scenario B** (structured call flow): `claim(token)` simulated directly
  → correctly reports the decoy wallet's full balance drained to the
  attacker wallet, verdict `critical`.
- Sanity check: a small, limited approval to an unregistered address
  correctly comes back `safe`.

Not yet done: MCP server wiring (Phase 6) is what will actually expose
`simulate_call()` to an agent as `simulate_wallet_interaction`.
