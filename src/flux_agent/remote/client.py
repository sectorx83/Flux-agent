"""Termux-friendly remote client for a Flux Agent host."""

from __future__ import annotations

import os

import httpx


class RemoteClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("FLUX_REMOTE_URL", "")).rstrip("/")
        self.token = token or os.getenv("FLUX_REMOTE_TOKEN", "")
        if not self.base_url.startswith("https://"):
            raise ValueError("Remote API URL must use HTTPS. Use a private VPN tunnel if needed.")
        if len(self.token) < 32:
            raise ValueError("FLUX_REMOTE_TOKEN must contain at least 32 characters.")

    def _request(self, method: str, path: str, **kwargs):
        response = httpx.request(
            method, f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=20, **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def submit(self, prompt: str, mode: str = "chat") -> dict:
        return self._request("POST", "/tasks", json={"prompt": prompt, "mode": mode})

    def tasks(self) -> dict:
        return self._request("GET", "/tasks")
