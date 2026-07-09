"""
In-memory rate limiter (Phase 6: "someone will hammer this with garbage
addresses"). Fixed-window per-identifier limiter, wired into the payment
wrapper's on_before_execution hook — keyed by the *payer's wallet address*
(extracted from the verified payment payload) rather than IP, since IP is
easy to rotate/spoof/share behind NAT but a payer address is the identity
that's already been cryptographically verified by the time this hook runs.

Deliberately simple (no Redis, no external store) — fine for a single
process; would need a shared store behind a load balancer.
"""
import time
from collections import defaultdict, deque

WINDOW_SECONDS = 60
MAX_CALLS_PER_WINDOW = 20

_call_log: dict[str, deque] = defaultdict(deque)


def _extract_payer(hook_ctx) -> str:
    """Best-effort extraction of the payer's address from the verified
    payment payload. Falls back to a shared bucket if the shape doesn't
    match what's expected — fails safe (still rate-limited), not open."""
    try:
        payload = hook_ctx.payment_payload.payload
        if isinstance(payload, dict):
            auth = payload.get("permit2Authorization") or payload.get("authorization") or {}
            payer = auth.get("from") or payload.get("from")
            if payer:
                return payer.lower()
    except Exception:
        pass
    return "unknown"


def check_rate_limit(hook_ctx) -> bool:
    """Returns True to allow execution, False to block it (the payment
    wrapper treats a False return as blocked, per its on_before_execution
    contract)."""
    payer = _extract_payer(hook_ctx)
    now = time.monotonic()
    log = _call_log[payer]

    while log and now - log[0] > WINDOW_SECONDS:
        log.popleft()

    if len(log) >= MAX_CALLS_PER_WINDOW:
        return False

    log.append(now)
    return True
