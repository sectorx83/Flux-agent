"""Signed plugin package verification and manifest-only installation."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from flux_agent.security.policy import DEFAULT_PERMISSIONS

MAX_PACKAGE_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_FILES = 256
SIGNATURE_FILE = "SIGNATURE.ed25519"


def build_signed_package(source_dir: Path, output_path: Path, private_key: str) -> Path:
    """Build a signed plugin ZIP from a directory containing manifest.json."""
    import os
    import tempfile

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise RuntimeError("Signed plugins require: pip install 'flux-agent[plugins]'") from exc
    try:
        key_bytes = base64.b64decode(private_key, validate=True)
        if len(key_bytes) != 32:
            raise ValueError("Ed25519 private key must decode to exactly 32 bytes.")
        signer = Ed25519PrivateKey.from_private_bytes(key_bytes)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid base64 Ed25519 private key.") from exc

    root = source_dir.expanduser().resolve()
    destination = output_path.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Plugin source must be a directory.")
    try:
        destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Output package must be outside the plugin source directory.")

    files: dict[str, bytes] = {}
    total_size = 0
    for item in sorted(root.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"Plugin source cannot contain symbolic links: {item}")
        if not item.is_file():
            continue
        relative = item.relative_to(root).as_posix()
        if relative == SIGNATURE_FILE or "\\" in relative or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
            raise ValueError(f"Invalid plugin source path: {relative}")
        content = item.read_bytes()
        total_size += len(content)
        if len(files) >= MAX_PACKAGE_FILES - 1 or total_size > MAX_PACKAGE_BYTES:
            raise ValueError("Plugin source exceeds package file-count or 25 MiB size limits.")
        files[relative] = content
    if "manifest.json" not in files:
        raise ValueError("Plugin source directory must contain manifest.json.")
    manifest = PluginRegistry._validate_manifest(json.loads(files["manifest.json"]))
    payload = {
        "manifest": manifest,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    files[SIGNATURE_FILE] = base64.b64encode(signer.sign(canonical))
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".flux-plugin-", suffix=".tmp", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                archive.writestr(name, content)
        if temporary.stat().st_size > MAX_PACKAGE_BYTES:
            raise ValueError("Compressed plugin package exceeds the 25 MiB size limit.")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


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

    def install_from_catalog(self, catalog_url: str, plugin_id: str, version: str, public_key: str) -> Path:
        """Install a package listed in a signed HTTPS catalog, then verify its package signature."""
        import tempfile
        from urllib.parse import urlparse

        import httpx
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        parsed_url = urlparse(catalog_url)
        if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise ValueError("Plugin catalog URL must be an HTTPS URL without embedded credentials.")
        try:
            key_bytes = base64.b64decode(public_key, validate=True)
            if len(key_bytes) != 32:
                raise ValueError("Ed25519 public key must decode to exactly 32 bytes.")
            verifier = Ed25519PublicKey.from_public_bytes(key_bytes)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid base64 Ed25519 public key.") from exc

        try:
            response = httpx.get(catalog_url, timeout=20, follow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 1024 * 1024:
                raise ValueError("Plugin catalog exceeds the 1 MiB size limit.")
            catalog = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError(f"Unable to retrieve plugin catalog: {exc}") from exc
        if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
            raise ValueError("Unsupported plugin catalog schema.")
        signature_text = catalog.pop("signature", None)
        if not isinstance(signature_text, str):
            raise ValueError("Plugin catalog is missing its signature.")
        canonical = json.dumps(catalog, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        try:
            verifier.verify(base64.b64decode(signature_text, validate=True), canonical)
        except Exception as exc:
            raise ValueError("Plugin catalog signature verification failed.") from exc

        entries = catalog.get("plugins")
        if not isinstance(entries, list):
            raise ValueError("Plugin catalog must contain a plugins list.")
        matches = [
            entry for entry in entries
            if isinstance(entry, dict) and entry.get("id") == plugin_id and entry.get("version") == version
        ]
        if len(matches) != 1:
            raise ValueError("The requested plugin and version must appear exactly once in the catalog.")
        entry = matches[0]
        package_url = entry.get("url")
        expected_hash = entry.get("sha256")
        parsed_package = urlparse(package_url) if isinstance(package_url, str) else None
        if (
            parsed_package is None or parsed_package.scheme != "https" or not parsed_package.hostname
            or parsed_package.username or parsed_package.password
            or not isinstance(expected_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_hash)
        ):
            raise ValueError("Catalog entry must provide an HTTPS package URL and SHA-256 digest.")
        try:
            package_response = httpx.get(package_url, timeout=30, follow_redirects=False)
            package_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ValueError(f"Unable to download plugin package: {exc}") from exc
        package_bytes = package_response.content
        if len(package_bytes) > MAX_PACKAGE_BYTES or hashlib.sha256(package_bytes).hexdigest() != expected_hash:
            raise ValueError("Plugin package size or catalog SHA-256 digest is invalid.")
        try:
            with zipfile.ZipFile(io.BytesIO(package_bytes)) as package_archive:
                package_manifest = self._validate_manifest(json.loads(package_archive.read("manifest.json")))
        except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Catalog package does not contain a valid plugin manifest.") from exc
        if package_manifest["id"] != plugin_id or package_manifest["version"] != version:
            raise ValueError("Downloaded package identity does not match the signed catalog entry.")
        with tempfile.NamedTemporaryFile(suffix=".fluxplugin", delete=False) as temporary:
            temporary.write(package_bytes)
            temporary_path = Path(temporary.name)
        try:
            return self.install_package(temporary_path, public_key)
        finally:
            temporary_path.unlink(missing_ok=True)

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
