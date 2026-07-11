"""
Session orchestration for the Interactive Live Sandbox (Layer 2).

Each session wraps a disposable Playwright Chromium browser context. The
browser is launched in incognito mode with no persistent user data directory,
and is torn down completely (context + browser closed, all caches/cookies
cleared) when the session ends.

Usage:
    async with Session() as session:
        await session.start("https://suspicious-site.example")
        page = session.page
        # ... interact with page ...
    # browser is fully torn down here
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from network_filter import NetworkFilter


@dataclass
class Session:
    """A disposable, per-session browser sandbox."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_url: Optional[str] = None
    _playwright: object = field(default=None, repr=False)
    _browser: Optional[Browser] = field(default=None, repr=False)
    _context: Optional[BrowserContext] = field(default=None, repr=False)
    _page: Optional[Page] = field(default=None, repr=False)
    _network_filter: Optional[NetworkFilter] = field(default=None, repr=False)

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    @property
    def browser(self) -> Optional[Browser]:
        return self._browser

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    async def start(self, target_url: str) -> Page:
        """Launch a disposable Chromium instance and navigate to target_url.

        The browser context is fully isolated: no persistent storage, no
        cookies from prior sessions, no user data directory.
        """
        self.target_url = target_url

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--no-first-run",
                "--disable-default-apps",
            ],
        )

        # Incognito context — no persistent state, no user_data_dir, spoof user agent
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,  # Malicious sites often have bad certs
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        self._page = await self._context.new_page()

        # Inject anti-fingerprinting stealth scripts
        stealth_path = Path(__file__).parent / "stealth.js"
        if stealth_path.exists():
            await self._page.add_init_script(path=str(stealth_path))

        # Apply network egress filtering
        self._network_filter = NetworkFilter(target_url)
        await self._network_filter.apply(self._page)

        await self._page.goto(target_url, wait_until="domcontentloaded")
        return self._page

    async def stop(self):
        """Tear down the session completely: close context, close browser,
        stop Playwright. No state persists between sessions."""
        errors = []

        if self._context:
            try:
                await self._context.clear_cookies()
            except Exception as e:
                errors.append(f"clear_cookies: {e}")
            try:
                await self._context.close()
            except Exception as e:
                errors.append(f"context.close: {e}")
            self._context = None
            self._page = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                errors.append(f"browser.close: {e}")
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                errors.append(f"playwright.stop: {e}")
            self._playwright = None

        self._network_filter = None

        if errors:
            print(f"[Session {self.session_id}] Teardown warnings: {errors}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False
