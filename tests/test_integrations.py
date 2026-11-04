import httpx
import pytest

from flux_agent.integrations.hub import IntegrationError, IntegrationHub


def _response(url, payload, status=200):
    return httpx.Response(status, json=payload, request=httpx.Request("GET", url))


def test_connector_status_reports_configuration_without_exposing_tokens(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    status = {item["name"]: item for item in IntegrationHub().status()}
    assert status["github"]["configured"] is True
    assert status["slack"]["configured"] is False
    assert "secret-token" not in str(status)


def test_github_issue_uses_official_api_and_version_headers(monkeypatch):
    captured = {}

    def request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return _response(url, {"number": 12, "html_url": "https://github.com/org/repo/issues/12"})

    monkeypatch.setenv("GITHUB_TOKEN", "gh-secret")
    monkeypatch.setattr("flux_agent.integrations.hub.httpx.request", request)
    result = IntegrationHub().create_github_issue("org/repo", "Bug", "Details")
    assert result["number"] == 12
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.github.com/repos/org/repo/issues"
    assert captured["headers"]["Authorization"] == "Bearer gh-secret"
    assert captured["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
    assert captured["json"] == {"title": "Bug", "body": "Details"}


def test_discord_uses_bot_authorization_scheme(monkeypatch):
    captured = {}

    def request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return _response(url, {"id": "message-1"})

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "discord-secret")
    monkeypatch.setattr("flux_agent.integrations.hub.httpx.request", request)
    result = IntegrationHub().send_message("discord", "12345", "Hello")
    assert result["message_id"] == "message-1"
    assert captured["headers"]["Authorization"] == "Bot discord-secret"


def test_notion_task_uses_database_title_property(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET":
            return _response(url, {"properties": {"Task name": {"type": "title"}}})
        return _response(url, {"id": "page-1", "url": "https://notion.so/page-1"})

    monkeypatch.setenv("NOTION_TOKEN", "notion-secret")
    monkeypatch.setattr("flux_agent.integrations.hub.httpx.request", request)
    result = IntegrationHub().create_notion_task("database-id", "Ship release", "Check CI")
    assert result["page_id"] == "page-1"
    assert calls[1][2]["json"]["properties"]["Task name"]["title"][0]["text"]["content"] == "Ship release"
    assert calls[0][2]["headers"]["Notion-Version"] == "2022-06-28"


def test_missing_credentials_fail_without_network(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(IntegrationError, match="GITHUB_TOKEN"):
        IntegrationHub().test("github")


def test_invalid_github_repository_is_rejected():
    with pytest.raises(ValueError, match="OWNER/REPO"):
        IntegrationHub().create_github_issue("not-a-repo", "Title", "Body")
