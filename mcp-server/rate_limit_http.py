"""
HTTP-layer rate limiting for auth_server.py (Phase 6: "someone will hammer
this with garbage addresses"). Same fixed-window, fail-safe design as
rate_limit.py (built earlier for the standalone x402 MCP server in this
same directory), adapted for plain FastAPI REST endpoints instead of the
x402 payment-wrapper hook — auth_server.py is the backend actually live
and called by the frontend, and had no rate limiting at all until now.

Deliberately simple (in-memory, single process) — matches the rest of this
server's local-first design (SQLite fallback, etc.); would need a shared
store (Redis) behind a load balancer or multiple worker processes.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._log: dict = defaultdict(deque)

    def check(self, identifier: str) -> None:
        now = time.monotonic()
        log = self._log[identifier]
        while log and now - log[0] > self.window_seconds:
            log.popleft()
        if len(log) >= self.max_calls:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {self.max_calls} calls per {self.window_seconds}s. Try again shortly.",
            )
        log.append(now)


# Pre-auth endpoints (nonce, login) have no verified identity yet — IP is
# the only signal available. Spoofable/shared behind NAT, but still enough
# to stop basic nonce-spam / brute-force login attempts.
_auth_limiter = RateLimiter(max_calls=10, window_seconds=60)

# Authenticated, expensive endpoints (audit, simulate) — real compute + a
# real on-chain attestation write per call. Keyed by the JWT-verified
# wallet address, a much stronger identity than IP.
_pipeline_limiter = RateLimiter(max_calls=10, window_seconds=60)

# Authenticated, cheap endpoints (api-keys, usage) — more generous, still
# capped so a misbehaving client can't hammer the DB in a tight loop.
_light_limiter = RateLimiter(max_calls=60, window_seconds=60)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def check_auth_rate_limit(request: Request) -> None:
    _auth_limiter.check(_client_ip(request))


def check_pipeline_rate_limit(wallet_address: str) -> None:
    _pipeline_limiter.check(wallet_address.lower())


def check_light_rate_limit(wallet_address: str) -> None:
    _light_limiter.check(wallet_address.lower())
