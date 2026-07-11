# Wallet Injection (`live-sandbox/wallet-inject`)

Contains the mock wallet provider scripts and injection machinery for the
Layer 2 Interactive Live Sandbox.

## Modules

### `eip1193_provider.js`
Full EIP-1193 compatible provider injected as `window.ethereum`:
- `isMetaMask = true` for maximum dApp compatibility
- Handles `eth_requestAccounts`, `eth_accounts`, `eth_chainId`, `net_version`,
  `wallet_switchEthereumChain`, `eth_getBalance`, `eth_estimateGas`, etc.
- **Intercepted methods**: `eth_sendTransaction`, `personal_sign`,
  `eth_signTypedData_v4`, `eth_sign` — forwarded to the Python interceptor
  via `window.__vetra_intercept()`, which routes them to the Layer 1
  simulation engine.
- EIP-6963 `announceProvider` event dispatched for newer dApps.
- Legacy `send()` / `sendAsync()` support for older dApps.

### `solana_provider.js`
Solana Wallet Standard mock provider injected as `window.solana` (Phantom-style):
- `isPhantom = true` for Phantom-compatible dApp detection.
- `connect()`, `signTransaction()`, `signAllTransactions()`, `signMessage()`,
  `signAndSendTransaction()` — all intercepted.
- Wallet Standard `register-wallet` event dispatched for newer dApps.

### `injector.py`
`WalletInjector` class:
- Uses `page.add_init_script()` to inject config globals + both provider
  scripts **before** any site JavaScript runs.
- Uses `page.expose_function("__vetra_intercept", ...)` to receive
  intercepted calls back in Python.
- `resolve_request()` / `reject_request()` — sends responses back to the
  page's pending JS promises.
- Configurable: `decoy_address`, `chain_id`, `solana_pubkey`, `on_intercept`
  callback.

## Dependency on `sandbox/`

The mock providers capture wallet interactions and route them to
`interceptor/`, which uses the existing `sandbox/` simulation engine to
inspect transaction outcomes.

## Tests

```sh
py -3.14 live-sandbox/wallet-inject/test_inject.py
```

Verifies:
- EIP-1193 provider injected with correct `isMetaMask`, accounts, chain ID
- Solana provider injected with correct `isPhantom`, public key
- Intercepted `eth_sendTransaction` triggers the Python callback
- Fake response returned to the page's JS correctly
