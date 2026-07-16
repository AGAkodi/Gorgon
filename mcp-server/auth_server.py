import os
import sys
import secrets
import hashlib
import subprocess
import time
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct
import requests
import jwt

from rate_limit_http import check_auth_rate_limit, check_pipeline_rate_limit, check_light_rate_limit
from pricing_config import VERDICT_PRICE_UI, SIMULATION_PRICE_UI

# Load env from workspace .env
env_path = Path(__file__).parent.parent / ".env"
env_vars = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env_vars[key.strip()] = val.strip()
        if key.strip() not in os.environ:
            os.environ[key.strip()] = val.strip()

# Inject path for attestation & sandbox
sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
sys.path.insert(0, str(Path(__file__).parent.parent / "sandbox"))
sys.path.insert(0, str(Path(__file__).parent.parent / "exploit-intel"))

from full_pipeline import run_verdict_pipeline
from simulate import simulate_call
from cache import cache_key
from deploy_contracts import deploy_sandbox, decoy_wallet_address, FORK_RPC as SANDBOX_FORK_RPC

# --- SQLite Local Fallback Database Helper ---
DB_FILE = Path(__file__).parent.parent / "vetra_local.db"

class LocalDBHelper:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    wallet_address TEXT,
                    created_at TEXT,
                    label TEXT,
                    last_used_at TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS wallet_sessions (
                    session_token TEXT PRIMARY KEY,
                    wallet_address TEXT,
                    expires_at TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS verdict_cache (
                    contract_hash TEXT PRIMARY KEY,
                    chain TEXT,
                    verdict TEXT,
                    attested_at TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    wallet_address TEXT,
                    tool_name TEXT,
                    called_at TEXT,
                    cost INTEGER
                )
            """)

    def save_session(self, session_token, wallet_address, expires_at):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO wallet_sessions (session_token, wallet_address, expires_at) VALUES (?, ?, ?)",
                (session_token, wallet_address.lower(), expires_at)
            )

    def get_session(self, session_token):
        cursor = self.conn.cursor()
        cursor.execute("SELECT wallet_address FROM wallet_sessions WHERE session_token = ?", (session_token,))
        row = cursor.fetchone()
        return row["wallet_address"] if row else None

    def get_api_keys(self, wallet_address):
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, wallet_address, created_at, label, last_used_at FROM api_keys WHERE wallet_address = ?", (wallet_address.lower(),))
        return [dict(row) for row in cursor.fetchall()]

    def create_api_key(self, hashed_key, wallet_address, label):
        with self.conn:
            self.conn.execute(
                "INSERT INTO api_keys (key, wallet_address, created_at, label) VALUES (?, ?, ?, ?)",
                (hashed_key, wallet_address.lower(), datetime.now(timezone.utc).isoformat(), label)
            )

    def delete_api_key(self, hashed_key, wallet_address):
        with self.conn:
            self.conn.execute(
                "DELETE FROM api_keys WHERE key = ? AND wallet_address = ?",
                (hashed_key, wallet_address.lower())
            )

    def get_usage_logs(self, wallet_address):
        cursor = self.conn.cursor()
        cursor.execute("SELECT tool_name, called_at, cost FROM usage_log WHERE wallet_address = ? ORDER BY called_at DESC", (wallet_address.lower(),))
        return [dict(row) for row in cursor.fetchall()]

    def add_usage_log(self, wallet_address, tool_name, cost):
        with self.conn:
            self.conn.execute(
                "INSERT INTO usage_log (wallet_address, tool_name, called_at, cost) VALUES (?, ?, ?, ?)",
                (wallet_address.lower(), tool_name, datetime.now(timezone.utc).isoformat(), cost)
            )

    def get_cached_verdict(self, contract_hash):
        cursor = self.conn.cursor()
        cursor.execute("SELECT verdict FROM verdict_cache WHERE contract_hash = ?", (contract_hash,))
        row = cursor.fetchone()
        return json.loads(row["verdict"]) if row else None

    def set_cached_verdict(self, contract_hash, chain, verdict_dict):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO verdict_cache (contract_hash, chain, verdict, attested_at) VALUES (?, ?, ?, ?)",
                (contract_hash, chain, json.dumps(verdict_dict), datetime.now(timezone.utc).isoformat())
            )

# --- FastAPI Initialization ---
app = FastAPI(title="Vetra API Gateway")

# CORS setup for the React frontend. Local dev origins are always allowed.
# In the single-deploy setup (Option 2) the frontend is served from this same
# server, so requests are same-origin and CORS never fires. FRONTEND_ORIGIN
# lets a separately-hosted frontend (Option 1 — e.g. Vercel) be allowed
# without a code change.
_cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"]
if os.environ.get("FRONTEND_ORIGIN"):
    _cors_origins.append(os.environ["FRONTEND_ORIGIN"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET", "vetra-jwt-secret-key-change-in-prod")

db_headers = {
    "apikey": SUPABASE_KEY if SUPABASE_KEY else "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json"
}

# Database Router Configuration
USE_SQLITE = False
db_helper = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/api_keys?limit=1", headers=db_headers, timeout=5)
        if resp.status_code == 404:
            print("WARNING: Supabase tables return 404. Falling back to local SQLite database.")
            USE_SQLITE = True
        elif resp.status_code >= 400:
            print(f"Supabase returned status {resp.status_code}. Falling back to local SQLite database.")
            USE_SQLITE = True
    except Exception as e:
        print(f"Failed to query Supabase: {e}. Falling back to local SQLite database.")
        USE_SQLITE = True
else:
    print("Supabase credentials missing. Falling back to local SQLite database.")
    USE_SQLITE = True

if USE_SQLITE:
    db_helper = LocalDBHelper()

# --- Sandbox environment (fork + mock contracts) ---
# Previously this was entirely manual: someone had to start the fork,
# run sandbox/deploy_contracts.py by hand, then hardcode the resulting
# addresses into the frontend. That breaks every time the fork restarts
# (fresh addresses) or SANDBOX_DECOY_WALLET_PRIVATE_KEY changes (as it did
# during an earlier .env desync) — the frontend's hardcoded decoy_wallet
# silently stopped matching the actual funded wallet. Fixed by making this
# server self-sufficient: ensure a fork is up (start one if not), deploy
# fresh contracts against it, and serve the real current addresses via
# /api/sandbox/config instead of anyone hardcoding them.
SANDBOX_CONFIG = None


def _fork_is_up(rpc_url: str) -> bool:
    try:
        resp = requests.post(
            rpc_url, timeout=3,
            json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
        )
        return resp.status_code == 200 and "result" in resp.json()
    except Exception:
        return False


def _ensure_sandbox_ready():
    global SANDBOX_CONFIG
    if not _fork_is_up(SANDBOX_FORK_RPC):
        print(f"[sandbox] EVM fork not reachable at {SANDBOX_FORK_RPC}, starting one...")
        fork_script = Path(__file__).parent.parent / "sandbox" / "fork" / "start-evm-fork.sh"
        try:
            if os.name == 'nt':
                subprocess.Popen(
                    ["bash", str(fork_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [str(fork_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[sandbox] WARNING: Failed to start fork process automatically: {e}")
            print(f"[sandbox] WARNING: /api/simulate and /api/sandbox/config will fail until fork is started manually.")
            return

        for _ in range(30):
            if _fork_is_up(SANDBOX_FORK_RPC):
                break
            time.sleep(1)
        else:
            print(f"[sandbox] WARNING: fork did not come up within 30s — /api/simulate and "
                  f"/api/sandbox/config will fail until it does. Check {fork_script} manually.")
            return

    try:
        decoy = decoy_wallet_address()
        SANDBOX_CONFIG = deploy_sandbox(decoy)
        print(f"[sandbox] ready: {SANDBOX_CONFIG}")
    except Exception as e:
        print(f"[sandbox] WARNING: contract deployment failed: {e}")


_ensure_sandbox_ready()

# Temporary challenge/nonces database in memory
challenges = {}  # wallet_address -> (nonce, message, expiry)

class LoginRequest(BaseModel):
    address: str
    message: str
    signature: str

class ApiKeyCreate(BaseModel):
    label: str

class AuditRequest(BaseModel):
    chain: str
    address: str
    source_code: str = ""

class SimulateRequest(BaseModel):
    chain: str
    decoy_wallet: str
    target: str
    tracked_tokens: list
    function_signature: str = None
    args: list = None
    calldata: str = None


# SIWE Nonce Generator
@app.get("/api/auth/nonce")
def get_nonce(request: Request, address: str):
    check_auth_rate_limit(request)
    if not address:
        raise HTTPException(status_code=400, detail="Address parameter is required")
    address = address.lower()
    nonce = secrets.token_hex(8)
    issued_at = datetime.now(timezone.utc).isoformat()
    
    # Format standard SIWE message
    message = (
        f"vetra.ai wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        f"To access the Vetra secure gateway and run transaction simulations.\n\n"
        f"Version: 1\n"
        f"Chain ID: 1952\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )
    
    challenges[address] = (nonce, message, time.time() + 300)
    return {"nonce": nonce, "message": message}


# SIWE Signature Verification
@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    check_auth_rate_limit(request)
    addr = req.address.lower()
    if addr not in challenges:
        raise HTTPException(status_code=400, detail="No active challenge for this address")
        
    nonce, expected_message, expiry = challenges[addr]
    if time.time() > expiry:
        del challenges[addr]
        raise HTTPException(status_code=400, detail="Challenge expired")
        
    # Verify the message is correct
    if req.message.strip() != expected_message.strip():
        raise HTTPException(status_code=400, detail="Message mismatch")
        
    # Verify signature
    try:
        recovered = Account.recover_message(encode_defunct(text=req.message), signature=req.signature)
        if recovered.lower() != addr:
            raise HTTPException(status_code=400, detail="Signature verification failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature format: {e}")
        
    # Clean up challenge
    del challenges[addr]
    
    # Issue JWT Token
    exp = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {
        "wallet_address": addr,
        "exp": exp
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # Store session in database/local SQLite
    if USE_SQLITE:
        db_helper.save_session(token, addr, exp.isoformat())
    else:
        session_data = {
            "session_token": token,
            "wallet_address": addr,
            "expires_at": exp.isoformat()
        }
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/wallet_sessions", headers=db_headers, json=session_data)
        if resp.status_code not in (200, 201):
            print(f"Supabase session save failed ({resp.status_code}): {resp.text}")
        
    return {"token": token, "walletAddress": addr}


# Dependency to verify token
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        
        # Verify session existence
        if USE_SQLITE:
            user_addr = db_helper.get_session(token)
            if user_addr:
                return user_addr
        else:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/wallet_sessions?session_token=eq.{token}",
                headers=db_headers
            )
            if resp.status_code == 200 and resp.json():
                return payload["wallet_address"]
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# API Keys Management
@app.get("/api/api-keys")
def get_api_keys(user: str = Depends(get_current_user)):
    check_light_rate_limit(user)
    if USE_SQLITE:
        return db_helper.get_api_keys(user)
    else:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/api_keys?wallet_address=eq.{user}", headers=db_headers)
        if resp.status_code == 200:
            return resp.json()
        raise HTTPException(status_code=resp.status_code, detail=resp.text)


@app.post("/api/api-keys")
def create_api_key(req: ApiKeyCreate, user: str = Depends(get_current_user)):
    check_light_rate_limit(user)
    raw_key = "vt_" + secrets.token_urlsafe(24)
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    
    if USE_SQLITE:
        db_helper.create_api_key(hashed_key, user, req.label)
        return {"raw_key": raw_key, "label": req.label, "key_hash": hashed_key}
    else:
        payload = {
            "key": hashed_key,
            "wallet_address": user,
            "label": req.label,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/api_keys", headers=db_headers, json=payload)
        if resp.status_code in (200, 201):
            return {"raw_key": raw_key, "label": req.label, "key_hash": hashed_key}
        raise HTTPException(status_code=resp.status_code, detail=resp.text)


@app.delete("/api/api-keys/{key_hash}")
def delete_api_key(key_hash: str, user: str = Depends(get_current_user)):
    check_light_rate_limit(user)
    if USE_SQLITE:
        db_helper.delete_api_key(key_hash, user)
        return {"status": "success"}
    else:
        resp = requests.delete(
            f"{SUPABASE_URL}/rest/v1/api_keys?key=eq.{key_hash}&wallet_address=eq.{user}",
            headers=db_headers
        )
        if resp.status_code in (200, 204):
            return {"status": "success"}
        raise HTTPException(status_code=resp.status_code, detail=resp.text)


# Usage Logs
@app.get("/api/usage")
def get_usage(user: str = Depends(get_current_user)):
    check_light_rate_limit(user)
    if USE_SQLITE:
        return db_helper.get_usage_logs(user)
    else:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/usage_log?wallet_address=eq.{user}", headers=db_headers)
        if resp.status_code == 200:
            return resp.json()
        raise HTTPException(status_code=resp.status_code, detail=resp.text)


# Health check — for uptime monitoring and container orchestration
# liveness/readiness probes. Deliberately cheap (no DB/RPC round trip) so
# it stays fast and doesn't itself become a source of false alarms.
@app.get("/health")
def health():
    return {"status": "ok", "db_backend": "sqlite" if USE_SQLITE else "supabase"}


# Pricing Config
@app.get("/api/pricing")
def get_pricing():
    return {
        "verdict_price": VERDICT_PRICE_UI,
        "simulation_price": SIMULATION_PRICE_UI
    }


# Verdict Pipeline Execution
@app.post("/api/audit")
def run_audit(req: AuditRequest, user: str = Depends(get_current_user)):
    check_pipeline_rate_limit(user)
    # Check cache first
    key = cache_key(req.chain, req.address, req.source_code)
    
    cached_verdict = None
    if USE_SQLITE:
        cached_verdict = db_helper.get_cached_verdict(key)
    else:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/verdict_cache?contract_hash=eq.{key}", headers=db_headers)
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                cached_verdict = rows[0]["verdict"]

    if cached_verdict:
        # Cache hit: Log usage with 0 cost (free cache hit!)
        if USE_SQLITE:
            db_helper.add_usage_log(user, "verdict_engine (cached)", 0)
        else:
            usage_payload = {
                "wallet_address": user,
                "tool_name": "verdict_engine (cached)",
                "cost": 0
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/usage_log", headers=db_headers, json=usage_payload)
        return {**cached_verdict, "cache_hit": True}

    # Cache miss: run full analysis pipeline
    try:
        verdict = run_verdict_pipeline(req.chain, req.address, req.source_code)
        
        # Log usage (cost 10)
        if USE_SQLITE:
            db_helper.add_usage_log(user, "verdict_engine", 10)
            db_helper.set_cached_verdict(key, req.chain, verdict)
        else:
            usage_payload = {
                "wallet_address": user,
                "tool_name": "verdict_engine",
                "cost": 10
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/usage_log", headers=db_headers, json=usage_payload)
            # Store in cache
            cache_payload = {
                "contract_hash": key,
                "chain": req.chain,
                "verdict": verdict
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/verdict_cache", headers=db_headers, json=cache_payload)
            
        return {**verdict, "cache_hit": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Sandbox environment config — the real, current addresses from this
# server's own fork/deployment, not something the frontend should hardcode.
@app.get("/api/sandbox/config")
def get_sandbox_config():
    if SANDBOX_CONFIG is None:
        raise HTTPException(
            status_code=503,
            detail="Sandbox environment not ready — the EVM fork or contract deployment "
                   "failed at server startup. Check the server logs for the [sandbox] warning.",
        )
    return SANDBOX_CONFIG


# Simulation Pipeline Execution
@app.post("/api/simulate")
def run_simulation(req: SimulateRequest, user: str = Depends(get_current_user)):
    check_pipeline_rate_limit(user)
    try:
        # Run Tenderly/Anvil simulation
        result = simulate_call(
            req.chain,
            req.decoy_wallet,
            req.target,
            req.tracked_tokens,
            req.function_signature,
            req.args,
            req.calldata
        )
        
        # Log usage (cost 20)
        if USE_SQLITE:
            db_helper.add_usage_log(user, "simulate_wallet_interaction", 20)
        else:
            usage_payload = {
                "wallet_address": user,
                "tool_name": "simulate_wallet_interaction",
                "cost": 20
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/usage_log", headers=db_headers, json=usage_payload)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Serve the built frontend (Option 2 — single deploy, same-origin).
# Registered LAST so every /api/* and /health route above wins first; this
# catch-all only handles everything else. If frontend/dist doesn't exist
# (e.g. backend-only Option 1 deploy, or local dev where Vite serves the UI),
# this is skipped entirely and the server is API-only as before.
# ---------------------------------------------------------------------------
FRONTEND_DIST = (Path(__file__).parent.parent / "frontend" / "dist").resolve()
if FRONTEND_DIST.is_dir():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve a real built asset if it exists (js/css/images/favicon),
        # otherwise fall back to index.html so client-side routes like
        # /dashboard and /sandbox resolve. The resolve()+startswith guard
        # blocks path traversal (e.g. ../../etc/passwd) out of dist.
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(FRONTEND_DIST)):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    print(f"[frontend] serving built SPA from {FRONTEND_DIST}")
else:
    print(f"[frontend] no build at {FRONTEND_DIST} — running API-only")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("AUTH_SERVER_PORT", "4023"))
    print(f"Starting Vetra Auth & Gateway Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
