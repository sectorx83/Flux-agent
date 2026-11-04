"""Manifest-only plugin registry; plugin code is never executed on discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from flux_agent.security.policy import DEFAULT_PERMISSIONS


@dataclass(frozen=True, slots=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str
    permissions: tuple[str, ...]
    manifest_path: Path


class PluginRegistry:
    def __init__(self, directory: Path) -> None:
        self.directory = directory.expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[PluginManifest]:
        found: list[PluginManifest] = []
        for manifest_path in sorted(self.directory.glob("*/plugin.json")):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            required = ("id", "name", "version")
            if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required):
                raise ValueError(f"Invalid plugin manifest: {manifest_path}")
            permissions = tuple(data.get("permissions", []))
            unknown = set(permissions) - DEFAULT_PERMISSIONS.keys()
            if unknown:
                raise ValueError(f"Plugin {data['id']} requests unknown permissions: {sorted(unknown)}")
            found.append(
                PluginManifest(
                    data["id"], data["name"], data["version"], data.get("description", ""),
                    permissions, manifest_path,
                )
            )
        return found

    def install_manifest(self, manifest: dict) -> Path:
        plugin_id = manifest.get("id", "")
        if not plugin_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in plugin_id):
            raise ValueError("Plugin id must contain lowercase letters, numbers, hyphens, or underscores.")
        destination = self.directory / plugin_id / "plugin.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Plugin already exists: {plugin_id}")
        destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.discover()
        return destination
