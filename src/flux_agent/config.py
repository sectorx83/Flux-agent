"""Configuration loading for Flux Agent."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_dir


@dataclass(frozen=True, slots=True)
class FluxConfig:
    provider: str = "groq"
    model: str = "openai/gpt-oss-120b"
    workspace: Path = Path.cwd()
    request_timeout: float = 90.0
    max_tool_rounds: int = 8
    fallback_providers: tuple[str, ...] = ()
    model_capabilities: dict[str, tuple[str, ...]] = field(default_factory=dict)


def default_config_path() -> Path:
    override = os.getenv("FLUX_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path(user_config_dir("flux-agent")) / "config.toml"


def load_config(path: Path | None = None) -> FluxConfig:
    config_path = path or default_config_path()
    data: dict = {}
    if config_path.is_file():
        with config_path.open("rb") as handle:
            loaded = tomllib.load(handle)
        data = loaded.get("flux", {})

    workspace_value = os.getenv("FLUX_WORKSPACE", data.get("workspace", "."))
    workspace = Path(workspace_value).expanduser().resolve()
    model = os.getenv("FLUX_MODEL", data.get("model", "openai/gpt-oss-120b"))
    fallbacks_raw = os.getenv("FLUX_FALLBACK_PROVIDERS", "")
    configured_fallbacks = data.get("fallback_providers", [])
    fallback_values = fallbacks_raw.split(",") if fallbacks_raw else configured_fallbacks
    fallbacks = tuple(item.strip() for item in fallback_values if item.strip())
    raw_capabilities = data.get("model_capabilities", {})
    if not isinstance(raw_capabilities, dict):
        raise ValueError("model_capabilities must be a TOML table keyed by exact model identifier.")
    capabilities: dict[str, tuple[str, ...]] = {}
    allowed_capabilities = {"chat", "tool_calling", "vision", "json_mode"}
    for model_name, values in raw_capabilities.items():
        if not isinstance(model_name, str) or not model_name.strip() or not isinstance(values, list):
            raise ValueError("Each model capability entry must be a model name and a list.")
        normalized = tuple(dict.fromkeys(str(value) for value in values))
        unknown = set(normalized) - allowed_capabilities
        if unknown:
            raise ValueError(f"Unknown model capabilities for {model_name}: {', '.join(sorted(unknown))}")
        capabilities[model_name] = normalized
    return FluxConfig(
        provider=data.get("provider", "groq"),
        model=model,
        workspace=workspace,
        request_timeout=float(data.get("request_timeout", 90.0)),
        max_tool_rounds=int(data.get("max_tool_rounds", 8)),
        fallback_providers=fallbacks,
        model_capabilities=capabilities,
    )
