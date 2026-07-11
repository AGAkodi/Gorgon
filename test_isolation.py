import os
import requests
import json
from eth_account import Account
from eth_account.messages import encode_defunct

# We will start the fast API server manually for this test or assume it's running
# Actually, I will just call the app directly using TestClient

# load .env manually
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

from fastapi.testclient import TestClient
import sys

# Ensure mcp-server is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "mcp-server")))
from auth_server import app

client = TestClient(app)

def run_test():
    print("=== Testing Wallet Isolation ===")
    
    # Generate Wallet A
    acct_a = Account.create()
    addr_a = acct_a.address
    
    # Generate Wallet B
    acct_b = Account.create()
    addr_b = acct_b.address

    print(f"Wallet A: {addr_a}")
    print(f"Wallet B: {addr_b}")

    # Login Wallet A
    nonce_resp_a = client.get(f"/api/auth/nonce?address={addr_a}")
    msg_a = nonce_resp_a.json()["message"]
    signable_a = encode_defunct(text=msg_a)
    sig_a = acct_a.sign_message(signable_a).signature.hex()
    
    login_a = client.post("/api/auth/login", json={"address": addr_a, "message": msg_a, "signature": sig_a})
    token_a = login_a.json()["token"]
    
    # Login Wallet B
    nonce_resp_b = client.get(f"/api/auth/nonce?address={addr_b}")
    msg_b = nonce_resp_b.json()["message"]
    signable_b = encode_defunct(text=msg_b)
    sig_b = acct_b.sign_message(signable_b).signature.hex()
    
    login_b = client.post("/api/auth/login", json={"address": addr_b, "message": msg_b, "signature": sig_b})
    token_b = login_b.json()["token"]

    print("\n--- Creating API Key for Wallet A ---")
    create_resp = client.post("/api/api-keys", json={"label": "Wallet A Main Key"}, headers={"Authorization": f"Bearer {token_a}"})
    print(create_resp.json())

    print("\n--- Fetching API Keys for Wallet A ---")
    fetch_a = client.get("/api/api-keys", headers={"Authorization": f"Bearer {token_a}"})
    keys_a = fetch_a.json()
    print(f"Found {len(keys_a)} keys for Wallet A: {[k['label'] for k in keys_a]}")

    print("\n--- Fetching API Keys for Wallet B ---")
    fetch_b = client.get("/api/api-keys", headers={"Authorization": f"Bearer {token_b}"})
    keys_b = fetch_b.json()
    print(f"Found {len(keys_b)} keys for Wallet B: {[k['label'] for k in keys_b]}")
    
    if len(keys_b) == 0:
        print("\nSUCCESS: Wallet B sees ZERO of Wallet A's keys.")
    else:
        print("\nFAILURE: Wallet B sees keys!")

if __name__ == "__main__":
    run_test()
