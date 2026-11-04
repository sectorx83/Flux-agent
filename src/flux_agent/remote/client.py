"""Termux-friendly remote client for a Flux Agent host."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import httpx


class RemoteClientError(ValueError):
    """Raised when a remote API request fails or returns invalid data."""


class RemoteClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("FLUX_REMOTE_URL", "")).rstrip("/")
        self.token = token or os.getenv("FLUX_REMOTE_TOKEN", "")
        if not self.base_url.startswith("https://"):
            raise ValueError("Remote API URL must use HTTPS. Use a private VPN tunnel if needed.")
        if len(self.token) < 32:
            raise ValueError("FLUX_REMOTE_TOKEN must contain at least 32 characters.")

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = httpx.request(
                method, f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=20, **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise RemoteClientError(f"Remote API request failed: {exc}") from exc
        except ValueError as exc:
            raise RemoteClientError("Remote API returned invalid JSON.") from exc

    def submit(self, prompt: str, mode: str = "chat") -> dict:
        return self._request("POST", "/tasks", json={"prompt": prompt, "mode": mode})

    def tasks(self) -> dict:
        return self._request("GET", "/tasks")

    def pair_device(self, device_name: str) -> dict:
        return self._request("POST", "/devices/pair", json={"device_name": device_name})

    def devices(self) -> dict:
        return self._request("GET", "/devices")

    def revoke_device(self, device_id: str) -> dict:
        return self._request("DELETE", f"/devices/{device_id}")

    def task(self, task_id: int) -> dict:
        if task_id < 1:
            raise ValueError("Task ID must be positive.")
        return self._request("GET", f"/tasks/{task_id}")

    def stream_task(self, task_id: int) -> Iterator[dict]:
        if task_id < 1:
            raise ValueError("Task ID must be positive.")
        try:
            with httpx.stream(
                "GET",
                f"{self.base_url}/tasks/{task_id}/stream",
                headers={"Authorization": f"Bearer {self.token}", "Accept": "text/event-stream"},
                timeout=None,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            yield json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as exc:
            raise RemoteClientError(f"Remote task stream failed: {exc}") from exc
