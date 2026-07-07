# mcp-server

MCP server exposing two tools to agents: `get_security_verdict` and
`simulate_wallet_interaction`. Deployed always-on (not localhost), with OKX
Payment SDK integration for pay-per-call billing.

## Hosting decision (Phase 0 — done)

**Own server (small always-on container), not serverless.**

Reasoning:

- Pay-per-call with no negotiation means callers expect consistent latency —
  serverless cold starts (Lambda/Vercel functions) are a bad fit for that.
- The MCP protocol expects a long-lived stateful connection per session, not
  discrete per-request function invocations.
- Simulation runs (Phase 5) hold a local fork (anvil / solana-test-validator)
  in memory — awkward to do inside a stateless function with an execution
  time limit.
- Judge/agent calls can arrive at any hour, so it needs a real uptime story
  (healthcheck + alerting), which is simpler to reason about on a container
  you control than a function's cold-start SLA.

Candidates: Fly.io, Railway, or a small VPS (Hetzner/DigitalOcean droplet)
running the server as a persistent process behind a process manager. Pick
whichever the deploy owner already has an account on — the requirement is
just "always-on container", not a specific vendor.

Not yet implemented — see Phase 6 in `TODO.md`.
