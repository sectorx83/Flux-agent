"""Playwright browser automation, installed through the browser optional extra."""

from __future__ import annotations

from urllib.parse import urlparse


class BrowserAutomation:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Install browser support with: pip install 'flux-agent[browser]'") from exc
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()

    async def navigate(self, url: str, approved: bool = False) -> str:
        if not approved:
            raise PermissionError("Browser navigation requires explicit approval.")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Browser navigation only accepts absolute HTTP or HTTPS URLs.")
        if self._page is None:
            raise RuntimeError("Browser is not started.")
        response = await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        title = await self._page.title()
        status = response.status if response else "unknown"
        return f"{status} · {title} · {self._page.url}"

    async def text(self, max_chars: int = 20_000) -> str:
        if self._page is None:
            raise RuntimeError("Browser is not started.")
        return (await self._page.locator("body").inner_text())[:max_chars]

    async def click(self, selector: str, approved: bool = False) -> None:
        if not approved:
            raise PermissionError("Browser interaction requires explicit approval.")
        if self._page is None:
            raise RuntimeError("Browser is not started.")
        await self._page.locator(selector).first.click(timeout=10_000)

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._browser = self._playwright = self._page = None
