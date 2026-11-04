import pytest

from flux_agent.browser.automation import BrowserAutomation


def test_browser_requires_approval_before_navigation():
    browser = BrowserAutomation()
    with pytest.raises(PermissionError, match="approval"):
        browser.navigate("https://example.com")


def test_browser_rejects_non_http_url_before_starting_browser():
    browser = BrowserAutomation()
    with pytest.raises(ValueError, match="HTTP"):
        browser.navigate("file:///etc/passwd", approved=True)


def test_browser_click_requires_approval():
    browser = BrowserAutomation()
    with pytest.raises(PermissionError, match="approval"):
        browser.click("button")
