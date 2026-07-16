# Vetra image — builds all backend services (auth_server.py, facilitator.py,
# server.py) AND the built React frontend from one image (they share the same
# Python dependency tree; the frontend is compiled in a separate node stage
# and copied in). See docker-compose.yml for how each service is run, and
# DEPLOYMENT.md for host-specific instructions (Railway/Fly.io/VPS).
#
# Which process a container runs is chosen by the start command, not this
# file's CMD:
#   - A2MCP listing endpoint : bash mcp-server/start_listing.sh
#   - Website + API (Option 2): bash mcp-server/start_web.sh
#   - default CMD below       : auth_server.py (API only)

# --- Stage 1: build the frontend (dist is .dockerignored, so build it here) ---
FROM node:20-slim AS frontend-build
WORKDIR /fe
RUN npm install -g pnpm
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install
COPY frontend/ ./
# Same-origin build: leave VITE_API_BASE_URL unset so the SPA uses relative
# /api URLs served by the same FastAPI process (Option 2). To point a build
# at a separate backend instead, pass --build-arg VITE_API_BASE_URL=...
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

# --- Stage 2: python runtime (backend + serves the built frontend) ---
FROM python:3.11-slim

# --- System deps ---
# curl/git: Foundry installer. build-essential: some pip packages
# (cryptography deps) need a compiler on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Foundry (cast/anvil) ---
# Needed by sandbox/simulate.py + sandbox/deploy_contracts.py (cast) and
# the EVM fork (anvil) for /api/simulate.
ENV FOUNDRY_DIR=/root/.foundry
ENV PATH="${FOUNDRY_DIR}/bin:${PATH}"
RUN curl -L https://foundry.paradigm.xyz | bash \
    && foundryup

# --- Python deps ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- solc (for Slither static analysis) ---
# NOTE: binaries.soliditylang.org has been observed slow/throttled from some
# network environments (confirmed directly during this project's own dev
# sandbox, not a one-off). If this build step hangs or times out, see the
# curl-based workaround in DEPLOYMENT.md rather than assume the version is
# wrong.
RUN solc-select install 0.8.20 && solc-select use 0.8.20

# --- App code ---
COPY . .

# Built frontend from stage 1 (frontend/dist is .dockerignored from the build
# context, so it must come from the node stage, not the COPY . . above).
# auth_server.py serves this when start_web.sh runs; the MCP/facilitator
# services simply ignore it.
COPY --from=frontend-build /fe/dist ./frontend/dist

EXPOSE 4021 4022 4023

# Actual command is set per-service in docker-compose.yml (auth_server.py /
# facilitator.py / server.py all live in mcp-server/).
CMD ["python3", "mcp-server/auth_server.py"]
