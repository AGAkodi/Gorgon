"""
Network egress filtering for the Interactive Live Sandbox (Layer 2).

Uses Playwright's route() API to intercept ALL network requests from the
sandboxed page. Only requests to the target domain, its subdomains, and
explicitly allowed asset origins (CDNs, font services) are permitted.
Everything else is blocked and logged.

This is NOT a full container-level firewall (that's the Hardening sub-phase),
but it prevents the sandboxed page from phoning home to arbitrary external
services or exfiltrating data through unexpected origins.
"""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Set

from playwright.async_api import Page, Route


def _is_internal_address(hostname: str) -> bool:
    """Returns True if the hostname resolves to loopback, private, or link-local IP."""
    if not hostname:
        return False
    
    hostname_lower = hostname.lower().strip("[]")
    if hostname_lower in ("localhost", "localhost.localdomain"):
        return True

    # Check if the hostname itself is a valid IP address
    try:
        ip = ipaddress.ip_address(hostname_lower)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # Not a raw IP address, try to resolve it
        try:
            # Resolve to IPs using getaddrinfo to support IPv4 & IPv6
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return True
        except Exception:
            # If resolution fails, it is not a resolvable internal address.
            # Allow the request to pass to standard networking (which will fail to resolve it).
            return False
    return False


# Common CDN / asset domains that legitimate sites load resources from.
# These are allowed by default to avoid breaking page rendering.
DEFAULT_ASSET_ALLOWLIST = frozenset({
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "ajax.googleapis.com",
    "maxcdn.bootstrapcdn.com",
    "stackpath.bootstrapcdn.com",
    "use.fontawesome.com",
    "kit.fontawesome.com",
    "ka-f.fontawesome.com",
})


class NetworkFilter:
    """Restricts page network egress to the target site and allowed assets."""

    def __init__(self, target_url: str, extra_allowlist: Set[str] = None):
        parsed = urlparse(target_url)
        self._target_domain = parsed.hostname or ""
        self._allowed_domains: Set[str] = set(DEFAULT_ASSET_ALLOWLIST)
        if extra_allowlist:
            self._allowed_domains |= extra_allowlist
        self._blocked_log: list = []

    @property
    def blocked_requests(self) -> list:
        """Returns a list of blocked request URLs (for debugging/logging)."""
        return list(self._blocked_log)

    def _is_allowed(self, url: str) -> bool:
        """Check if a request URL is allowed through the filter."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Block loopback, private IP ranges, and link-local metadata endpoints
        if _is_internal_address(hostname):
            return False

        # Allow same-domain and subdomains of the target
        if hostname == self._target_domain:
            return True
        if hostname.endswith(f".{self._target_domain}"):
            return True

        # Allow explicitly whitelisted asset domains
        if hostname in self._allowed_domains:
            return True

        # Allow data: and blob: URIs (inline page assets)
        if parsed.scheme in ("data", "blob"):
            return True

        return False

    async def _handle_route(self, route: Route):
        """Playwright route handler: allow or block each request."""
        url = route.request.url

        if self._is_allowed(url):
            await route.continue_()
        else:
            self._blocked_log.append(url)
            await route.abort("blockedbyclient")

    async def apply(self, page: Page):
        """Install the network filter on a Playwright page.

        Must be called BEFORE navigating to the target URL so that all
        requests (including the initial document load's sub-resources) are
        filtered.
        """
        # Intercept all URLs
        await page.route("**/*", self._handle_route)
