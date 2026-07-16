# Deployment (Phase 6 — artifacts only, not deployed)

This documents how to take Vetra's backend to an always-on host, and how
to set up uptime monitoring once it's there. **Nothing here has been
deployed or provisioned — no hosting account or monitoring account was
created on your behalf.** Docker isn't available in the dev environment
this was written in, so the `Dockerfile`/`docker-compose.yml` below are
reviewed carefully but not build-tested here — build and smoke-test them
yourself before trusting them in production.

## Frontend: point it at the deployed backend

The frontend used to have `http://localhost:4023` hardcoded in 6 files —
fixed (`frontend/src/lib/api.js` is now the single source of truth,
everything imports `API_BASE_URL` from there). To deploy the frontend
pointed at a real backend instead of your laptop, set one env var at
build time:

```sh
# Vercel/Netlify/Cloudflare Pages: set this in the project's env var settings
VITE_API_BASE_URL=https://your-deployed-backend-url
```

Without it, the built frontend falls back to `http://localhost:4023` —
which is correct for local dev, but means a deployed frontend with this
unset will silently try to reach your own machine and fail. Set it
explicitly for any non-local deployment.

## What actually needs to run

| Service | File | Port | Talked to by |
|---|---|---|---|
| Auth gateway | `mcp-server/auth_server.py` | 4023 | The frontend, directly. This is the one that matters most — it's live today. |
| x402 facilitator | `mcp-server/facilitator.py` | 4022 | The MCP server, for payment verify/settle. |
| MCP server | `mcp-server/server.py` | 4021 | Real AI agents, over MCP + x402 pay-per-call. Not yet adopted by anything live. |
| EVM fork | `anvil` (Foundry) | 8545/8555 | `auth-server`'s `/api/simulate` and `mcp-server`'s `simulate_wallet_interaction`. |

All three Python services share one dependency tree (`requirements.txt`) —
that's why one `Dockerfile` builds all of them; `docker-compose.yml` just
runs each with a different `command`.

## Required environment variables

Everything in `.env` (see `.env.example`). The ones that matter most for a
production deploy specifically:

- `ATTESTATION_WALLET_PRIVATE_KEY` / `ATTESTATION_CONTRACT_ADDRESS` — real funds-adjacent, keep these as host secrets (Fly.io secrets, Railway variables), never baked into the image or committed.
- `X_LAYER_TESTNET_RPC_URL`, `PAYMENT_TOKEN_ADDRESS`, `FACILITATOR_URL` — `FACILITATOR_URL` needs to point at wherever `facilitator.py` actually ends up running (the compose setup below uses the internal service name `facilitator`; adjust if you split these across separate hosts).
- `GROQ_API_KEY` (and `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` if you add them) — also a secret, not a build-time value.
- `NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — same.

## Option 0: $0 cost — Oracle Cloud "Always Free" (recommended if budget is the constraint)

Verified directly (not assumed) as of writing: this is the only genuinely
free-forever, always-on option among the common choices. **Fly.io removed
its free tier in 2024** — new signups get a 7-day/2-VM-hour trial, then it
costs money. **Railway's free tier is $1/month of credit after the first
month** — explicitly not meant for always-on hosting, services pause when
credit runs out. Oracle Cloud's Always Free tier is different: real
infrastructure, no expiration, no charge, as long as you stay within the
free allowance.

What you get: 2 ARM (Ampere A1) OCPUs + 12GB RAM, always-on, $0 forever
(reduced from 4 OCPU/24GB in June 2026 — older guides online will say the
bigger number). Enough to run this project's `docker-compose.yml`.

```sh
# 1. Sign up at cloud.oracle.com (needs a card on file for identity
#    verification — Always Free resources are not charged to it)
# 2. Create a VM.Standard.A1.Flex instance (the Always Free ARM shape),
#    Ubuntu, in a region with Always Free capacity available
#    (capacity is sometimes exhausted in popular regions — try a few if
#    the first one says no capacity)
# 3. SSH in, install Docker:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out/in after this

# 4. Clone this repo, fill in .env, then:
docker compose up -d
```

**Real caveat, not glossed over:** this Dockerfile/compose setup has only
been reviewed for x86_64, not build-tested on ARM64 at all (Docker isn't
available in this dev environment, so neither architecture has actually
been build-tested — see the note at the top of this file). `python:3.11-slim`
and Foundry both publish ARM64 builds, so those should be fine; `solc`
(via `solc-select`) is the one piece I'm genuinely unsure has ARM64 Linux
binaries for every version — check `solc-select install 0.8.20` actually
succeeds on the instance before assuming the rest of the build will work,
and fall back to a version you confirm has an aarch64 binary if not.

**Also worth knowing:** Oracle can reclaim an Always Free instance that
sits idle/underutilized. Point your uptime monitor at it (see below) —
that's exactly the kind of thing it exists to catch.

## Option A0: A2MCP listing endpoint only — one Railway service (fastest path to submitting)

This is the deploy that the **OKX.AI A2MCP listing** actually needs, and
nothing more. The listing points agents at a single public URL: the MCP
server's SSE endpoint. That endpoint internally depends on the x402
facilitator and an anvil EVM fork, but neither of those should be public —
so all three run in **one container / one Railway service** via
`mcp-server/start_listing.sh`, which boots them in dependency order
(fork → facilitator → MCP server, health-gated) and binds the MCP server to
Railway's injected `$PORT`. The website + `auth_server.py` are a *separate*,
optional deploy (the human-facing dashboard) and are not required to list.

```sh
# In Railway: New Project → Deploy from this repo (it builds the root Dockerfile).
# Then, on the service:
#   Settings → Start Command:   bash mcp-server/start_listing.sh
#   Settings → Networking:      Generate Domain (this public URL is what you
#                               paste into the OKX A2MCP listing)
#   Variables:                  set every real secret from .env (see below) —
#                               NOT committed; .env is gitignored + dockerignored.
```

Minimum variables this service needs (from `.env`): `GROQ_API_KEY`
(+ `GROQ_MODEL` if pinning a model), `X_LAYER_TESTNET_RPC_URL`,
`ATTESTATION_WALLET_PRIVATE_KEY`, `ATTESTATION_CONTRACT_ADDRESS`,
`PAYMENT_TOKEN_ADDRESS`, `PAYMENT_NETWORK`, and
`SANDBOX_DECOY_WALLET_PRIVATE_KEY`. Leave `FACILITATOR_PORT`/`EVM_FORK_PORT`
at their defaults so `FACILITATOR_URL=http://127.0.0.1:4022` and
`EVM_FORK_RPC_URL=http://127.0.0.1:8555` stay internally consistent — don't
override just one of the pair.

Verified locally before writing this: `start_listing.sh` boots all three in
order and the resulting endpoint answers MCP tool discovery
(`get_security_verdict`, `simulate_wallet_interaction`, `health`) and a
spec-correct x402 `402` challenge (amount/asset/network). It has **not** been
build-tested inside Docker on this machine (no Docker here — same caveat as
the top of this file), so do one `docker build` + a `bash
mcp-server/start_listing.sh` smoke run on the host before trusting it live.

The A2MCP registration itself (register your Agentic Wallet, install Onchain
OS, register as an A2MCP ASP, submit the listing) happens through your own
OKX agent per OKX's flow — this deploy just gives you the public,
x402-compliant endpoint URL that step needs.

## Option A0b: Website + API in one service (Option 2 — single deploy, no CORS)

The human-facing site (marketing pages + Verdict Dashboard + Sandbox) and the
API it calls, as **one Railway service** with **one public URL**. The FastAPI
auth server serves the built React frontend from the same origin, so there's
no CORS to configure and no separate `VITE_API_BASE_URL` to set. This is
independent of the A2MCP listing above — it's the human UI, not the agent
endpoint, and it does **not** gate the OKX submission.

```sh
# In Railway: New Project → Deploy from this repo (builds the root Dockerfile,
# which is multi-stage: a node stage compiles frontend/dist, the python stage
# serves it). Then on the service:
#   Settings → Start Command:   bash mcp-server/start_web.sh
#   Settings → Networking:      Generate Domain
#   Variables:                  the same secrets as Option A0, PLUS the
#                               Supabase vars if using Supabase instead of the
#                               bundled SQLite fallback.
```

How it works: `frontend/dist` is `.dockerignore`d, so the Dockerfile builds it
in a `node:20-slim` stage and copies it into the python image. `auth_server.py`
detects `frontend/dist` at startup and serves it (SPA fallback to `index.html`
for client routes like `/dashboard`); if the build isn't present it silently
runs API-only. `api.js` uses relative `/api` URLs in a production build (unset
`VITE_API_BASE_URL`), so the browser calls the same origin. `auth_server.py`
self-provisions its own EVM fork on startup, so no fork sidecar is needed here.

Verified locally (native, not in Docker — Docker still unavailable here): built
the frontend, restarted the auth server, loaded the site from its own origin,
and confirmed `/`, `/dashboard`, and `/assets/*` serve correctly while `/api/*`
and `/health` still hit the real handlers, and a real audit runs same-origin
end to end. Do a `docker build` on the host to confirm the multi-stage build
before trusting it live.

Prefer the frontend on a CDN instead? Set `VITE_API_BASE_URL` at build time to
this service's URL, deploy `frontend/` to Vercel (there's a `vercel.json` for
SPA routing), and set `FRONTEND_ORIGIN=<your-vercel-url>` on this service so
CORS allows it. That's Option 1 — two deploys, CDN frontend.

## Option A: Fly.io (costs money — no longer has a free tier)

```sh
fly launch --no-deploy          # generates fly.toml from the Dockerfile, don't deploy yet
fly secrets set ATTESTATION_WALLET_PRIVATE_KEY=... GROQ_API_KEY=... # etc., one per real secret in .env
fly deploy
```

Fly.io's generated `fly.toml` will default to running the Dockerfile's
`CMD` (`auth_server.py`). For `facilitator.py`/`server.py`/the EVM fork,
either run them as separate Fly apps (simplest — `fly launch` again in a
copy of this repo with a different `Dockerfile` `CMD`), or use Fly's
[Processes](https://fly.io/docs/apps/processes/) feature to run multiple
process groups from one app.

## Option B: Railway (costs money beyond a small first-month credit)

Railway can build directly from this `Dockerfile`. Create one service per
row in the table above (4 services total), pointing each at this repo with
a different start command override (`python3 mcp-server/auth_server.py`,
etc.), and set the env vars per-service in Railway's dashboard. Railway
auto-provides a public URL and TLS per service — use that for
`FACILITATOR_URL` instead of the docker-compose internal hostname.

## Option C: Plain paid VPS (Hetzner/DigitalOcean droplet, ~$5-6/mo) + docker-compose

```sh
# On the VPS, with Docker + docker-compose installed:
git clone <this repo>
cd Vetra
cp .env.example .env   # fill in real secrets
docker compose up -d
docker compose logs -f auth-server   # confirm it started cleanly
curl http://localhost:4023/health
```

This is the most direct path to "always-on container you control" (the
reasoning in `mcp-server/README.md`'s original hosting decision) since it
runs exactly what's in `docker-compose.yml` with no platform-specific
translation.

Put this behind a reverse proxy (Caddy or nginx) for TLS + a real domain —
not included here since the certificate/domain is your decision to make,
not something to generate for you.

## Known build risk: solc download

`binaries.soliditylang.org` was observed slow/throttled from this
project's own dev sandbox earlier — direct confirmation, not a guess (a
`solc-select install` hung indefinitely; a direct `curl` with a 60s
timeout completed but only transferred ~3.6KB/s). This is very likely
specific to that sandboxed environment, not a general internet condition —
real hosting providers typically have unthrottled bandwidth to public
CDNs — but if `solc-select install 0.8.20` in the `Dockerfile` hangs or
times out on your build host too:

```sh
# Get the exact filename for your version from the list first:
curl -s https://binaries.soliditylang.org/macosx-amd64/list.json | grep '"0.8.20"'
mkdir -p ~/.solc-select/artifacts/solc-0.8.20
curl -L -o ~/.solc-select/artifacts/solc-0.8.20/solc-0.8.20 \
  "https://binaries.soliditylang.org/<platform>/<exact-filename-from-above>"
chmod +x ~/.solc-select/artifacts/solc-0.8.20/solc-0.8.20
solc-select use 0.8.20
```

## Operational note: the EVM fork isn't stateless

`anvil` holds fork state in memory for the process lifetime. The
`docker-compose.yml` here runs one long-lived fork shared by all
simulation requests — fine for a demo/hackathon volume, but means
concurrent simulations share fork state (one simulation's on-chain effects
are visible to the next). If real concurrent traffic becomes a concern,
the fix is spinning up a fresh `anvil` per simulation request rather than
sharing one — a real architecture change, not configuration, so flagging
it here rather than solving it silently.

## Health check endpoint

`auth_server.py`: `GET /health` → `{"status": "ok", "db_backend": "sqlite"|"supabase"}`
`facilitator.py`: `GET /health` → `{"status": "ok"}` (already existed)

Both are deliberately cheap (no DB/RPC round trip) so they don't become a
source of false alarms themselves.

## Uptime monitoring (documented, not configured — no account created)

Any of these work on a free tier; pick whichever you're comfortable
creating an account with:

- **UptimeRobot** (uptimerobot.com) — simplest. Add an HTTP(S) monitor
  pointed at `https://<your-host>/health` on the auth-server, 5-minute
  interval, alert via email/Slack/webhook.
- **Better Uptime** (betteruptime.com) — similar, nicer status-page
  option if you want a public status page for the listing.
- **Healthchecks.io** — more of a "dead man's switch" model (pings *out*
  from your server); less natural fit here since our health check is a
  passive endpoint to be polled, not something that pings out.

Configure it against `/health` on whichever host ends up running
`auth_server.py` — that's the one that matters (it's what the frontend and
judges/users actually depend on being up). Add a second monitor on
`facilitator.py`'s `/health` if the MCP server / real agent payments are
part of what you're demoing.
