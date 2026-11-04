"""Signed plugin package verification and manifest-only installation."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from flux_agent.security.policy import DEFAULT_PERMISSIONS

MAX_PACKAGE_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_FILES = 256
SIGNATURE_FILE = "SIGNATURE.ed25519"


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

    @staticmethod
    def _validate_manifest(data: object) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Plugin manifest must be a JSON object.")
        required = ("id", "name", "version")
        if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required):
            raise ValueError("Plugin manifest requires non-empty id, name, and version.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", data["id"]):
            raise ValueError("Plugin id must use lowercase letters, numbers, hyphens, or underscores.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", data["version"]):
            raise ValueError("Plugin version contains unsupported characters.")
        permissions = data.get("permissions", [])
        if not isinstance(permissions, list) or any(not isinstance(item, str) for item in permissions):
            raise ValueError("Plugin permissions must be a list of strings.")
        unknown = set(permissions) - DEFAULT_PERMISSIONS.keys()
        if unknown:
            raise ValueError(f"Plugin {data['id']} requests unknown permissions: {sorted(unknown)}")
        return data

    def discover(self) -> list[PluginManifest]:
        found: list[PluginManifest] = []
        for manifest_path in sorted(self.directory.glob("*/plugin.json")):
            data = self._validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
            found.append(
                PluginManifest(
                    data["id"], data["name"], data["version"], data.get("description", ""),
                    tuple(data.get("permissions", [])), manifest_path,
                )
            )
        return found

    def install_manifest(self, manifest: dict) -> Path:
        data = self._validate_manifest(manifest)
        destination = self.directory / data["id"] / "plugin.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Plugin already exists: {data['id']}")
        destination.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.discover()
        return destination

    def install_package(self, package_path: Path, public_key: str) -> Path:
        """Verify an Ed25519-signed ZIP and store it without executing its contents.

        The signature covers canonical JSON containing the validated manifest and
        SHA-256 hashes of every package file except the detached signature itself.
        The public key is a base64-encoded 32-byte Ed25519 key.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except ImportError as exc:
            raise RuntimeError("Signed plugins require: pip install 'flux-agent[plugins]'") from exc

        try:
            key_bytes = base64.b64decode(public_key, validate=True)
            if len(key_bytes) != 32:
                raise ValueError("Ed25519 public key must decode to exactly 32 bytes.")
            verifier = Ed25519PublicKey.from_public_bytes(key_bytes)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid base64 Ed25519 public key.") from exc

        package_path = package_path.expanduser().resolve()
        if not package_path.is_file() or package_path.stat().st_size > MAX_PACKAGE_BYTES:
            raise ValueError("Plugin package is missing or exceeds the 25 MiB size limit.")

        try:
            with zipfile.ZipFile(package_path) as archive:
                entries = archive.infolist()
                if not entries or len(entries) > MAX_PACKAGE_FILES:
                    raise ValueError("Plugin package must contain between 1 and 256 files.")
                files: dict[str, bytes] = {}
                total_size = 0
                for entry in entries:
                    name = entry.filename
                    relative = PurePosixPath(name)
                    if (
                        relative.is_absolute() or not relative.parts
                        or any(part in {"", ".", ".."} for part in relative.parts)
                        or "\\\\" in name or name in files or entry.is_dir()
                    ):
                        raise ValueError(f"Unsafe or duplicate plugin package path: {name}")
                    mode = entry.external_attr >> 16
                    if mode and (mode & 0o170000) == 0o120000:
                        raise ValueError(f"Symbolic links are not allowed in plugin packages: {name}")
                    total_size += entry.file_size
                    if total_size > MAX_PACKAGE_BYTES:
                        raise ValueError("Plugin package expands beyond the 25 MiB size limit.")
                    files[name] = archive.read(entry)
        except zipfile.BadZipFile as exc:
            raise ValueError("Plugin package is not a valid ZIP archive.") from exc

        if "manifest.json" not in files or SIGNATURE_FILE not in files:
            raise ValueError("Plugin package requires manifest.json and SIGNATURE.ed25519.")
        try:
            manifest = self._validate_manifest(json.loads(files["manifest.json"]))
            signature = base64.b64decode(files[SIGNATURE_FILE].strip(), validate=True)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid plugin package metadata: {exc}") from exc

        signed_payload = {
            "manifest": manifest,
            "files": {
                name: hashlib.sha256(content).hexdigest()
                for name, content in sorted(files.items()) if name != SIGNATURE_FILE
            },
        }
        canonical = json.dumps(signed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        try:
            verifier.verify(signature, canonical)
        except Exception as exc:
            raise ValueError("Plugin signature verification failed.") from exc

        plugin_dir = self.directory / manifest["id"]
        destination = plugin_dir / "plugin.json"
        if destination.exists():
            raise FileExistsError(f"Plugin already exists: {manifest['id']}")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        package_destination = plugin_dir / f"{manifest['version']}.fluxplugin"
        package_destination.write_bytes(package_path.read_bytes())
        return package_destination
