"""Official API adapters for common collaboration and task services.

Credentials are read from environment variables and are never persisted by Flux.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class IntegrationError(RuntimeError):
    """Raised when an integration API request fails."""


@dataclass(frozen=True, slots=True)
class IntegrationSpec:
    name: str
    credential_env: str
    test_url: str
    auth_scheme: str = "Bearer"


SPECS = {
    "github": IntegrationSpec("github", "GITHUB_TOKEN", "https://api.github.com/user"),
    "slack": IntegrationSpec("slack", "SLACK_BOT_TOKEN", "https://slack.com/api/auth.test"),
    "discord": IntegrationSpec("discord", "DISCORD_BOT_TOKEN", "https://discord.com/api/users/@me", "Bot"),
    "telegram": IntegrationSpec("telegram", "TELEGRAM_BOT_TOKEN", "https://api.telegram.org"),
    "google": IntegrationSpec("google", "GOOGLE_ACCESS_TOKEN", "https://www.googleapis.com/oauth2/v3/userinfo"),
    "notion": IntegrationSpec("notion", "NOTION_TOKEN", "https://api.notion.com/v1/users/me"),
}


class IntegrationHub:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def status(self) -> list[dict[str, str | bool]]:
        return [
            {
                "name": spec.name,
                "credential": spec.credential_env,
                "configured": bool(os.getenv(spec.credential_env, "").strip()),
            }
            for spec in SPECS.values()
        ]

    def _token(self, service: str) -> str:
        if service not in SPECS:
            raise ValueError(f"Unsupported integration: {service}")
        token = os.getenv(SPECS[service].credential_env, "").strip()
        if not token:
            raise IntegrationError(f"{SPECS[service].credential_env} is not configured.")
        return token

    def _request(
        self, service: str, method: str, url: str, *, json_body: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = self._token(service)
        headers = {"Authorization": f"{SPECS[service].auth_scheme} {token}"}
        if extra_headers:
            headers.update(extra_headers)
        if service == "notion":
            headers["Notion-Version"] = "2022-06-28"
        try:
            response = httpx.request(
                method, url, headers=headers, json=json_body, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("message") or exc.response.json().get("error") or exc.response.text
            except ValueError:
                detail = exc.response.text
            raise IntegrationError(
                f"{service} API returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise IntegrationError(f"{service} request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise IntegrationError(f"{service} returned an unexpected response.")
        if service == "slack" and payload.get("ok") is False:
            raise IntegrationError(f"Slack API error: {payload.get('error', 'unknown_error')}")
        if service == "telegram" and payload.get("ok") is False:
            raise IntegrationError(f"Telegram API error: {payload.get('description', 'unknown_error')}")
        return payload

    def test(self, service: str) -> dict[str, Any]:
        spec = SPECS.get(service)
        if spec is None:
            raise ValueError(f"Unsupported integration: {service}")
        url = spec.test_url
        if service == "telegram":
            url = f"https://api.telegram.org/bot{self._token(service)}/getMe"
            try:
                response = httpx.get(url, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise IntegrationError(f"telegram request failed: {exc}") from exc
            if not payload.get("ok"):
                raise IntegrationError(f"Telegram API error: {payload.get('description', 'unknown_error')}")
            return {"service": service, "connected": True, "identity": payload.get("result", {}).get("username")}
        payload = self._request(
            service, "GET", url,
            extra_headers={"Notion-Version": "2022-06-28"} if service == "notion" else None,
        )
        identity = (
            payload.get("login") or payload.get("name") or payload.get("user_id")
            or payload.get("team") or payload.get("email") or payload.get("id")
        )
        return {"service": service, "connected": True, "identity": identity}

    def send_message(self, service: str, target: str, message: str) -> dict[str, Any]:
        if not target.strip() or not message.strip():
            raise ValueError("Message target and content cannot be empty.")
        if service == "slack":
            payload = self._request(
                service, "POST", "https://slack.com/api/chat.postMessage",
                json_body={"channel": target, "text": message},
            )
            return {"service": service, "message_id": payload.get("ts"), "channel": payload.get("channel")}
        if service == "discord":
            channel = quote(target, safe="")
            payload = self._request(
                service, "POST", f"https://discord.com/api/v10/channels/{channel}/messages",
                json_body={"content": message},
            )
            return {"service": service, "message_id": payload.get("id"), "channel": target}
        if service == "telegram":
            token = self._token(service)
            try:
                response = httpx.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": target, "text": message}, timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise IntegrationError(f"telegram request failed: {exc}") from exc
            if not payload.get("ok"):
                raise IntegrationError(f"Telegram API error: {payload.get('description', 'unknown_error')}")
            return {"service": service, "message_id": payload.get("result", {}).get("message_id")}
        raise ValueError("Message delivery is supported for slack, discord, and telegram.")

    def create_github_issue(self, repository: str, title: str, body: str) -> dict[str, Any]:
        parts = repository.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Repository must use OWNER/REPO format.")
        if not title.strip():
            raise ValueError("Issue title cannot be empty.")
        owner, name = (quote(part, safe="") for part in parts)
        payload = self._request(
            "github", "POST", f"https://api.github.com/repos/{owner}/{name}/issues",
            json_body={"title": title, "body": body},
            extra_headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        )
        return {"service": "github", "number": payload.get("number"), "url": payload.get("html_url")}

    def create_google_task(self, task_list_id: str, title: str, notes: str = "") -> dict[str, Any]:
        if not task_list_id.strip() or not title.strip():
            raise ValueError("Google task list ID and title are required.")
        task_list = quote(task_list_id, safe="")
        payload = self._request(
            "google", "POST",
            f"https://tasks.googleapis.com/tasks/v1/lists/{task_list}/tasks",
            json_body={"title": title, "notes": notes},
        )
        return {"service": "google", "task_id": payload.get("id"), "title": payload.get("title")}

    def create_notion_task(self, database_id: str, title: str, description: str = "") -> dict[str, Any]:
        if not database_id.strip() or not title.strip():
            raise ValueError("Notion database ID and task title are required.")
        database_id = quote(database_id, safe="")
        database = self._request(
            "notion", "GET", f"https://api.notion.com/v1/databases/{database_id}"
        )
        title_property = next(
            (name for name, value in database.get("properties", {}).items()
             if value.get("type") == "title"),
            None,
        )
        if title_property is None:
            raise IntegrationError("The selected Notion database has no title property.")
        children = []
        if description.strip():
            children.append(
                {"object": "block", "type": "paragraph", "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": description[:2000]}}]
                }}
            )
        payload = self._request(
            "notion", "POST", "https://api.notion.com/v1/pages",
            json_body={
                "parent": {"database_id": database_id},
                "properties": {title_property: {"title": [{"text": {"content": title[:2000]}}]}},
                "children": children,
            },
        )
        return {"service": "notion", "page_id": payload.get("id"), "url": payload.get("url")}
