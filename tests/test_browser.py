import asyncio

import pytest

from flux_agent.browser.automation import BrowserAutomation


def test_browser_requires_approval_before_navigation():
    browser = BrowserAutomation()
    with pytest.raises(PermissionError, match="approval"):
        asyncio.run(browser.navigate("https://example.com"))


def test_browser_rejects_non_http_url():
    browser = BrowserAutomation()
    with pytest.raises(ValueError, match="HTTP"):
        asyncio.run(browser.navigate("file:///etc/passwd", approved=True))
