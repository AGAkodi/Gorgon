# Interactive Live Sandbox (Layer 2)

This module implements the Layer 2 Interactive Live Sandbox capability for Vetra. It merges live malicious site rendering with Vetra's existing Layer 1 transaction simulation engine (`sandbox/`) into an isolated, interactive session.

## Module Structure

- **`orchestration/`**: Handles the session container lifecycle (disposable Playwright/Chromium instances, egress network rules, and teardown).
- **`streaming/`**: Handles real-time browser view streaming (CDP screencast frames or WebRTC) to the frontend.
- **`wallet-inject/`**: Contains the EIP-1193 mock wallet provider (`window.ethereum`) and the Solana wallet-standard equivalent injected before page load.
- **`interceptor/`**: Catches signature/transaction requests, forwards them to the existing Layer 1 `sandbox/` engine, and returns plausible fake responses to the site.

## Dependencies

- **`sandbox/`**: This Layer 2 sandbox relies entirely on the existing Layer 1 simulation engine in `sandbox/` for executing transaction impacts and generating wallet impact reports. It **imports** and reuses those functions directly, avoiding duplication of simulation logic.
