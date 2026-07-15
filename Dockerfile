# Vetra backend image — builds mcp-server/auth_server.py, facilitator.py,
# and server.py from one image (they share the same Python dependency
# tree). See docker-compose.yml for how each service is actually run, and
# DEPLOYMENT.md for host-specific instructions (Fly.io/Railway/VPS).
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

EXPOSE 4021 4022 4023

# Actual command is set per-service in docker-compose.yml (auth_server.py /
# facilitator.py / server.py all live in mcp-server/).
CMD ["python3", "mcp-server/auth_server.py"]
