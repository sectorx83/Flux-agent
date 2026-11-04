"""Groq's OpenAI-compatible chat completions adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ProviderError(RuntimeError):
    """Raised when an AI provider request fails."""


class GroqProvider:
    def __init__(self, model: str, timeout: float = 90.0) -> None:
        self.model = model
        self.timeout = timeout
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.last_usage: dict[str, Any] = {}
        self.last_model = model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("GROQ_API_KEY is not set. Add it to your environment or .env file.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach Groq: {exc}") from exc

        if response.is_error:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                detail = response.text
            raise ProviderError(f"Groq returned HTTP {response.status_code}: {detail}")
        try:
            payload = response.json()
            self.last_usage = payload.get("usage") or {}
            self.last_model = payload.get("model") or self.model
            return payload["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Groq returned an unexpected response format.") from exc
