"""Synchronous Playwright browser automation for the agent tool loop."""

from __future__ import annotations

from urllib.parse import urlparse


class BrowserAutomation:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Install browser support with: pip install 'flux-agent[browser]'") from exc
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()
        except Exception:
            self._playwright.stop()
            self._playwright = None
            raise

    def navigate(self, url: str, approved: bool = False) -> str:
        if not approved:
            raise PermissionError("Browser navigation requires explicit approval.")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Browser navigation only accepts absolute HTTP or HTTPS URLs.")
        if self._page is None:
            self.start()
        response = self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        title = self._page.title()
        status = response.status if response else "unknown"
        return f"{status} · {title} · {self._page.url}"

    def text(self, max_chars: int = 20_000) -> str:
        if self._page is None:
            raise RuntimeError("Browser is not started.")
        if max_chars < 1:
            raise ValueError("max_chars must be positive.")
        return self._page.locator("body").inner_text()[:max_chars]

    def click(self, selector: str, approved: bool = False) -> None:
        if not approved:
            raise PermissionError("Browser interaction requires explicit approval.")
        if self._page is None:
            raise RuntimeError("Browser is not started.")
        if not selector.strip():
            raise ValueError("A non-empty CSS selector is required.")
        self._page.locator(selector).first.click(timeout=10_000)

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
            self._browser = self._playwright = self._page = None
