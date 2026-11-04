"""Provider routing with optional OpenAI-compatible fallbacks."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from flux_agent.providers.groq import GroqProvider, ProviderError


class ChatProvider(Protocol):
    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    name: str
    base_url: str
    key_env: str
    default_model: str


MODEL_CAPABILITIES: dict[str, frozenset[str]] = {
    "openai/gpt-oss-120b": frozenset({"chat", "tool_calling"}),
    "gemini-2.5-flash": frozenset({"chat", "tool_calling"}),
    "gpt-oss-120b": frozenset({"chat", "tool_calling"}),
}

PROVIDERS = {
    "groq": ProviderSpec("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "gemini": ProviderSpec(
        "gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-2.5-flash"
    ),
    "cerebras": ProviderSpec(
        "cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "gpt-oss-120b"
    ),
    "openrouter": ProviderSpec(
        "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai/gpt-oss-120b"
    ),
}


class CompatibleProvider:
    def __init__(self, spec: ProviderSpec, model: str | None = None, timeout: float = 90.0) -> None:
        self.spec = spec
        self.model = model or os.getenv(f"FLUX_{spec.name.upper()}_MODEL") or spec.default_model
        self.timeout = timeout
        self.api_key = os.getenv(spec.key_env, "").strip()
        self.last_usage: dict[str, Any] = {}
        self.last_model = self.model

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError(f"{self.spec.key_env} is not configured.")
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0.2}
        if tools:
            payload.update(tools=tools, tool_choice="auto")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.spec.name == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/sectorx83/Flux-agent"
            headers["X-Title"] = "Flux Agent"
        try:
            response = httpx.post(
                f"{self.spec.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.spec.name} network error: {exc}") from exc
        if response.is_error:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                detail = response.text
            raise ProviderError(f"{self.spec.name} HTTP {response.status_code}: {detail}")
        try:
            payload = response.json()
            self.last_usage = payload.get("usage") or {}
            self.last_model = payload.get("model") or self.model
            return payload["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.spec.name} returned an invalid chat response.") from exc


class ProviderRouter:
    def __init__(
        self, primary: str = "groq", fallbacks: tuple[str, ...] = (), model: str | None = None,
        timeout: float = 90.0, model_capabilities: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        names = tuple(dict.fromkeys((primary, *fallbacks)))
        unknown = [name for name in names if name not in PROVIDERS]
        if unknown:
            raise ValueError(f"Unknown provider(s): {', '.join(unknown)}")
        self.providers: list[tuple[str, ChatProvider]] = []
        for index, name in enumerate(names):
            spec = PROVIDERS[name]
            selected_model = model if index == 0 else None
            if name == "groq":
                provider: ChatProvider = GroqProvider(selected_model or spec.default_model, timeout)
            else:
                provider = CompatibleProvider(spec, selected_model, timeout)
            self.providers.append((name, provider))
        self.active_provider = primary
        self.active_model = getattr(self.providers[0][1], "model", model or PROVIDERS[primary].default_model)
        self.model_capabilities = {
            **{name: set(values) for name, values in MODEL_CAPABILITIES.items()},
            **{name: set(values) for name, values in (model_capabilities or {}).items()},
        }
        self._usage_store = None

    def _record_usage(self, provider: str, model: str, usage: dict[str, Any]) -> None:
        try:
            if self._usage_store is None:
                from pathlib import Path

                from platformdirs import user_data_dir

                from flux_agent.usage.store import UsageStore

                path = Path(user_data_dir("flux-agent")) / "usage.sqlite3"
                self._usage_store = UsageStore(path)
            self._usage_store.record(provider, model, usage)
        except (OSError, ValueError, sqlite3.Error):
            # Usage accounting must never turn a successful model response into a failed turn.
            return

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        failures: list[str] = []
        required = {"chat"}
        if tools:
            required.add("tool_calling")
        for message in messages:
            content = message.get("content")
            if isinstance(content, list) and any(
                isinstance(part, dict) and part.get("type") in {"image", "image_url"}
                for part in content
            ):
                required.add("vision")
        for name, provider in self.providers:
            model_name = getattr(provider, "model", "")
            capabilities = self.model_capabilities.get(model_name, {"chat"})
            missing = required - capabilities
            if missing:
                failures.append(
                    f"{name}/{model_name} lacks required capabilities: {', '.join(sorted(missing))}"
                )
                continue
            try:
                result = provider.chat(messages, tools)
                self.active_provider = name
                self.active_model = getattr(provider, "last_model", model_name)
                usage = getattr(provider, "last_usage", {})
                if usage:
                    self._record_usage(name, getattr(provider, "last_model", ""), usage)
                return result
            except ProviderError as exc:
                failures.append(str(exc))
                if "HTTP 401" in str(exc) or "HTTP 403" in str(exc):
                    continue
        raise ProviderError("All configured providers failed: " + " | ".join(failures))
