/**
 * EIP-1193 Mock Wallet Provider for the Interactive Live Sandbox (Layer 2).
 *
 * Injected into the sandboxed page as `window.ethereum` before any site JS
 * runs. Presents itself as MetaMask-compatible so dApps detect a wallet.
 *
 * Transaction and signing requests (eth_sendTransaction, personal_sign,
 * eth_signTypedData_v4) are intercepted and forwarded to the Python
 * interceptor via `window.__vetra_intercept(method, params)`, which routes
 * them to the Layer 1 simulation engine. The provider returns a promise
 * that resolves with the interceptor's fake response so the site's own
 * success/failure flow continues without breaking.
 *
 * Configuration is injected by the Python injector as globals:
 *   window.__VETRA_DECOY_ADDRESS  — the decoy wallet address
 *   window.__VETRA_CHAIN_ID       — hex chain ID (default "0x1")
 */

(function () {
  "use strict";

  const DECOY_ADDRESS = (window.__VETRA_DECOY_ADDRESS || "0x0d3c000000000000000000000000000000f00001").toLowerCase();
  const CHAIN_ID = window.__VETRA_CHAIN_ID || "0x1";

  // Pending intercept callbacks: requestId → { resolve, reject }
  const pendingRequests = new Map();
  let requestCounter = 0;

  // Event listeners
  const listeners = {};

  function emit(event, ...args) {
    const handlers = listeners[event] || [];
    for (const handler of handlers) {
      try {
        handler(...args);
      } catch (e) {
        console.error(`[Vetra] Event handler error for ${event}:`, e);
      }
    }
  }

  /**
   * Forward an intercepted method call to the Python interceptor and
   * return a promise that resolves with the fake response.
   */
  function interceptAndForward(method, params) {
    const requestId = ++requestCounter;

    return new Promise((resolve, reject) => {
      pendingRequests.set(requestId, { resolve, reject });

      // Call into the Python-exposed function
      if (typeof window.__vetra_intercept === "function") {
        window.__vetra_intercept(JSON.stringify({
          requestId: requestId,
          method: method,
          params: params,
        }));
      } else {
        // Fallback: if interceptor isn't wired yet, return a generic fake
        console.warn("[Vetra] Interceptor not available, returning fallback");
        resolve(generateFallbackResponse(method));
        pendingRequests.delete(requestId);
      }
    });
  }

  /**
   * Called by the Python interceptor to resolve a pending request.
   * Exposed as window.__vetra_intercept_resolve(requestId, resultJSON)
   */
  window.__vetra_intercept_resolve = function (requestId, resultJSON) {
    const pending = pendingRequests.get(requestId);
    if (pending) {
      pendingRequests.delete(requestId);
      try {
        pending.resolve(JSON.parse(resultJSON));
      } catch (e) {
        pending.resolve(resultJSON);
      }
    }
  };

  /**
   * Called by the Python interceptor to reject a pending request.
   */
  window.__vetra_intercept_reject = function (requestId, errorMessage) {
    const pending = pendingRequests.get(requestId);
    if (pending) {
      pendingRequests.delete(requestId);
      pending.reject(new Error(errorMessage));
    }
  };

  function generateFallbackResponse(method) {
    if (method === "eth_sendTransaction") {
      // Fake tx hash
      return "0x" + Array.from({ length: 64 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join("");
    }
    if (method === "personal_sign" || method === "eth_signTypedData_v4") {
      // Fake 65-byte ECDSA signature
      return "0x" + Array.from({ length: 130 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join("");
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // EIP-1193 Provider
  // ---------------------------------------------------------------------------

  const provider = {
    isMetaMask: true,
    isVetraSandbox: true,
    _metamask: {
      isUnlocked: () => Promise.resolve(true),
    },

    selectedAddress: DECOY_ADDRESS,
    chainId: CHAIN_ID,
    networkVersion: String(parseInt(CHAIN_ID, 16)),

    /**
     * EIP-1193 request method — the primary interface dApps use.
     */
    async request({ method, params }) {
      switch (method) {
        // --- Account methods ---
        case "eth_requestAccounts":
        case "eth_accounts":
          return [DECOY_ADDRESS];

        // --- Chain methods ---
        case "eth_chainId":
          return CHAIN_ID;

        case "net_version":
          return String(parseInt(CHAIN_ID, 16));

        case "wallet_switchEthereumChain":
          // Pretend to switch — don't actually change anything
          return null;

        case "wallet_addEthereumChain":
          // Pretend to add — don't actually change anything
          return null;

        // --- Balance & block methods (return plausible defaults) ---
        case "eth_getBalance":
          // Return 10 ETH in wei (hex)
          return "0x8AC7230489E80000";

        case "eth_blockNumber":
          return "0x" + (19000000).toString(16);

        case "eth_estimateGas":
          return "0x5208"; // 21000

        case "eth_gasPrice":
          return "0x3B9ACA00"; // 1 gwei

        case "eth_getTransactionCount":
          return "0x0";

        // --- INTERCEPTED METHODS (forwarded to Layer 1 simulation) ---
        case "eth_sendTransaction":
          return interceptAndForward(method, params);

        case "personal_sign":
          return interceptAndForward(method, params);

        case "eth_signTypedData":
        case "eth_signTypedData_v3":
        case "eth_signTypedData_v4":
          return interceptAndForward(method, params);

        case "eth_sign":
          return interceptAndForward(method, params);

        // --- Catch-all: log and return null ---
        default:
          console.log(`[Vetra] Unhandled method: ${method}`, params);
          return null;
      }
    },

    /**
     * Legacy send method (some older dApps still use this).
     */
    send(methodOrPayload, callbackOrParams) {
      if (typeof methodOrPayload === "string") {
        // send(method, params) style
        return provider.request({
          method: methodOrPayload,
          params: callbackOrParams || [],
        });
      }
      // send({ method, params }, callback) style
      const { method, params } = methodOrPayload;
      provider
        .request({ method, params })
        .then((result) => callbackOrParams(null, { result }))
        .catch((error) => callbackOrParams(error, null));
    },

    /**
     * Legacy sendAsync method.
     */
    sendAsync(payload, callback) {
      provider
        .request({ method: payload.method, params: payload.params })
        .then((result) =>
          callback(null, {
            id: payload.id,
            jsonrpc: "2.0",
            result,
          })
        )
        .catch((error) => callback(error, null));
    },

    // --- Event emitter interface ---
    on(event, handler) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(handler);
      return provider;
    },

    removeListener(event, handler) {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((h) => h !== handler);
      }
      return provider;
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

  // Install as window.ethereum
  Object.defineProperty(window, "ethereum", {
    value: provider,
    writable: false,
    configurable: false,
  });

  // Emit connection event
  setTimeout(() => {
    emit("connect", { chainId: CHAIN_ID });
  }, 0);

  // Also dispatch the standard EIP-6963 announcement event for newer dApps
  const announce = () => {
    try {
      window.dispatchEvent(
        new CustomEvent("eip6963:announceProvider", {
          detail: {
            info: {
              uuid: "vetra-sandbox-0001",
              name: "Vetra Sandbox Wallet",
              icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>",
              rdns: "dev.vetra.sandbox",
            },
            provider: provider,
          },
        })
      );
    } catch (e) {
      // EIP-6963 not supported in this context — fine, most sites use window.ethereum
    }
  };

  window.addEventListener("eip6963:requestProvider", announce);
  announce();

  console.log("[Vetra] EIP-1193 mock provider injected as window.ethereum");
})();

