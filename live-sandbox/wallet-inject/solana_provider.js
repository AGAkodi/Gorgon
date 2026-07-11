/**
 * Solana Wallet Standard Mock Provider for the Interactive Live Sandbox (Layer 2).
 *
 * Injected into the sandboxed page as `window.solana` (Phantom-style) and
 * also registered via the Wallet Standard `registerWallet()` API for newer
 * dApps.
 *
 * Transaction signing requests (signTransaction, signAllTransactions,
 * signMessage) are intercepted and forwarded to the Python interceptor via
 * `window.__vetra_intercept(method, params)`.
 *
 * Configuration is injected by the Python injector as globals:
 *   window.__VETRA_SOLANA_PUBKEY  — base58 public key string
 */

(function () {
  "use strict";

  // A plausible-looking Solana public key (32 bytes, base58)
  const MOCK_PUBKEY = window.__VETRA_SOLANA_PUBKEY ||
    "VeTrA1111111111111111111111111111111111111111";

  const listeners = {};
  let requestCounter = 0;
  const pendingRequests = new Map();

  function emit(event, ...args) {
    const handlers = listeners[event] || [];
    for (const handler of handlers) {
      try {
        handler(...args);
      } catch (e) {
        console.error(`[Vetra Solana] Event handler error for ${event}:`, e);
      }
    }
  }

  function interceptAndForward(method, params) {
    const requestId = ++requestCounter + 100000; // offset to avoid collision with EVM IDs

    return new Promise((resolve, reject) => {
      pendingRequests.set(requestId, { resolve, reject });

      if (typeof window.__vetra_intercept === "function") {
        window.__vetra_intercept(JSON.stringify({
          requestId: requestId,
          method: method,
          params: params,
          chain: "solana",
        }));
      } else {
        console.warn("[Vetra Solana] Interceptor not available, returning fallback");
        resolve(generateFallbackSignature());
        pendingRequests.delete(requestId);
      }
    });
  }

  // Resolution handlers — shared with EVM provider via window globals
  const origResolve = window.__vetra_intercept_resolve;
  window.__vetra_intercept_resolve = function (requestId, resultJSON) {
    const pending = pendingRequests.get(requestId);
    if (pending) {
      pendingRequests.delete(requestId);
      try {
        pending.resolve(JSON.parse(resultJSON));
      } catch (e) {
        pending.resolve(resultJSON);
      }
    } else if (origResolve) {
      origResolve(requestId, resultJSON);
    }
  };

  const origReject = window.__vetra_intercept_reject;
  window.__vetra_intercept_reject = function (requestId, errorMessage) {
    const pending = pendingRequests.get(requestId);
    if (pending) {
      pendingRequests.delete(requestId);
      pending.reject(new Error(errorMessage));
    } else if (origReject) {
      origReject(requestId, errorMessage);
    }
  };

  function generateFallbackSignature() {
    // 64-byte fake signature as Uint8Array
    const sig = new Uint8Array(64);
    for (let i = 0; i < 64; i++) {
      sig[i] = Math.floor(Math.random() * 256);
    }
    return { signature: sig };
  }

  // Mock PublicKey-like object
  const publicKey = {
    toString: () => MOCK_PUBKEY,
    toBase58: () => MOCK_PUBKEY,
    toBytes: () => new Uint8Array(32),
    toBuffer: () => new Uint8Array(32).buffer,
    equals: (other) => other && other.toString() === MOCK_PUBKEY,
  };

  // ---------------------------------------------------------------------------
  // Phantom-style Solana Provider (window.solana)
  // ---------------------------------------------------------------------------

  const provider = {
    isPhantom: true,
    isVetraSandbox: true,
    publicKey: publicKey,
    isConnected: true,

    async connect() {
      emit("connect");
      return { publicKey: publicKey };
    },

    async disconnect() {
      emit("disconnect");
    },

    async signTransaction(transaction) {
      // Serialize the transaction to a JSON-friendly form for interception
      const txData = serializeTransaction(transaction);
      const result = await interceptAndForward("signTransaction", txData);
      // Return the original transaction object (site expects it back)
      // with a fake signature attached
      if (transaction && typeof transaction === "object") {
        transaction._vetraIntercepted = true;
      }
      return transaction;
    },

    async signAllTransactions(transactions) {
      const results = [];
      for (const tx of transactions) {
        results.push(await provider.signTransaction(tx));
      }
      return results;
    },

    async signMessage(message, display) {
      const msgData = {
        message: message instanceof Uint8Array
          ? Array.from(message)
          : String(message),
        display: display || "utf8",
      };
      return interceptAndForward("signMessage", msgData);
    },

    async signAndSendTransaction(transaction, options) {
      await provider.signTransaction(transaction);
      // Return a fake signature string
      return {
        signature: Array.from({ length: 88 }, () =>
          "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[
            Math.floor(Math.random() * 62)
          ]
        ).join(""),
      };
    },

    // Event emitter
    on(event, handler) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(handler);
      return provider;
    },

    off(event, handler) {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((h) => h !== handler);
      }
      return provider;
    },

    removeListener(event, handler) {
      return provider.off(event, handler);
    },

    removeAllListeners(event) {
      if (event) {
        delete listeners[event];
      } else {
        Object.keys(listeners).forEach((k) => delete listeners[k]);
      }
      return provider;
    },
  };

  function serializeTransaction(tx) {
    try {
      if (tx && typeof tx.serialize === "function") {
        return { serialized: Array.from(tx.serialize()) };
      }
      if (tx && typeof tx.toJSON === "function") {
        return tx.toJSON();
      }
      // Best-effort: extract known fields
      return {
        feePayer: tx?.feePayer?.toString(),
        recentBlockhash: tx?.recentBlockhash,
        instructions: tx?.instructions?.map((ix) => ({
          programId: ix?.programId?.toString(),
          keys: ix?.keys?.map((k) => ({
            pubkey: k?.pubkey?.toString(),
            isSigner: k?.isSigner,
            isWritable: k?.isWritable,
          })),
          data: ix?.data ? Array.from(ix.data) : [],
        })),
      };
    } catch (e) {
      return { raw: String(tx) };
    }
  }

  // Install as window.solana (Phantom-style)
  Object.defineProperty(window, "solana", {
    value: provider,
    writable: false,
    configurable: false,
  });

  // Wallet Standard registration (for newer dApps)
  try {
    if (typeof window.navigator !== "undefined") {
      const walletStandardWallet = {
        name: "Vetra Sandbox Wallet",
        icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>",
        chains: ["solana:mainnet", "solana:devnet", "solana:testnet"],
        features: {
          "standard:connect": { connect: () => provider.connect() },
          "standard:disconnect": { disconnect: () => provider.disconnect() },
          "solana:signTransaction": { signTransaction: (tx) => provider.signTransaction(tx) },
          "solana:signMessage": { signMessage: (msg) => provider.signMessage(msg) },
        },
        accounts: [{
          address: MOCK_PUBKEY,
          publicKey: new Uint8Array(32),
          chains: ["solana:mainnet"],
          features: ["solana:signTransaction", "solana:signMessage"],
        }],
      };

      // Dispatch wallet-standard registration event
      window.dispatchEvent(
        new CustomEvent("wallet-standard:register-wallet", {
          detail: { register: (callback) => callback(walletStandardWallet) },
        })
      );
    }
  } catch (e) {
    // Wallet Standard not supported — fine, window.solana is the primary interface
  }

  console.log("[Vetra] Solana mock provider injected as window.solana");
})();
