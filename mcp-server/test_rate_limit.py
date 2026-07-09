#!/usr/bin/env python3
"""
Unit test for the rate limiter (Phase 6: "someone will hammer this with
garbage addresses"). Runs in isolation, not through the full paid MCP flow
— that's already exercised by test_client.py; this just proves the limiter
itself trips correctly and doesn't cross-contaminate between payers.

Usage: python3 mcp-server/test_rate_limit.py
"""
from types import SimpleNamespace

import rate_limit


def make_ctx(payer: str):
    return SimpleNamespace(
        payment_payload=SimpleNamespace(payload={"permit2Authorization": {"from": payer}})
    )


def main():
    rate_limit._call_log.clear()
    rate_limit.MAX_CALLS_PER_WINDOW = 5  # lower for a fast test

    payer_a = "0xAAAA000000000000000000000000000000AAAA"
    payer_b = "0xBBBB000000000000000000000000000000BBBB"

    for i in range(5):
        assert rate_limit.check_rate_limit(make_ctx(payer_a)) is True, f"call {i} should be allowed"
    assert rate_limit.check_rate_limit(make_ctx(payer_a)) is False, "6th call should be blocked"
    print("PASS: payer A blocked after exceeding limit")

    assert rate_limit.check_rate_limit(make_ctx(payer_b)) is True, "different payer should have its own bucket"
    print("PASS: payer B unaffected by payer A's limit (separate buckets)")

    unknown_ctx = SimpleNamespace(payment_payload=SimpleNamespace(payload={}))
    for i in range(5):
        assert rate_limit.check_rate_limit(unknown_ctx) is True
    assert rate_limit.check_rate_limit(unknown_ctx) is False
    print("PASS: malformed/unextractable payer falls back to a shared bucket, still rate-limited (fails safe)")

    print("\nAll rate limiter checks passed.")


if __name__ == "__main__":
    main()
