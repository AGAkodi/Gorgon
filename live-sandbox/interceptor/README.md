# Transaction Interception (`live-sandbox/interceptor`)

This subdirectory contains the logic to capture transaction and signing requests, run them through the Layer 1 simulation engine, and return safe mock values to the originating dApp.

## Modules

### `fake_responses.py`
Generates syntactically correct fallback data structures so the dApp's Javascript flows don't crash when transaction requests are simulated instead of executed:
- `fake_tx_hash()`: Generates a random `0x`-prefixed 32-byte (64 character) hex string.
- `fake_eth_signature()`: Generates a random `0x`-prefixed 65-byte (130 character) hex signature, ensuring the recovery ID byte is set to a realistic `1b` or `1c`.
- `fake_solana_signature()`: Generates a random 64-byte base58-encoded signature string.

### `handler.py`
`InterceptHandler` class coordinates the interception:
- Intercepts EVM `eth_sendTransaction` calls and:
  1. Extracts `to`, `data`, and value parameter values.
  2. Routes them through `sandbox/simulate.py:simulate_call()`.
  3. Returns a plausible fake transaction hash to the page.
- Intercepts signature requests (`personal_sign`, `eth_signTypedData_v4`, etc.) and Solana wallet interactions (`signTransaction`, `signMessage`) and returns mock signature results.
- Broadly supports graceful degradation if the Anvil fork is not active or token tracking is disabled, logging a warning and proceeding with a fallback `caution` status without crashing the container context.

## Tests

Run the following command to test the interceptor suite:
```sh
py -3.14 live-sandbox/interceptor/test_intercept.py
```

Verifies:
- Plausible format outputs for fake transaction hashes and signatures.
- Correct parsing of incoming EIP-1193 intercept payloads.
- Graceful degradation and fallback summaries when the simulation backend is unavailable.
