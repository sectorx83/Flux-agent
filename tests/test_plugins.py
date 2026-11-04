import json
from pathlib import Path

import pytest

from flux_agent.integrations.plugins import PluginRegistry


def test_plugin_manifest_discovery(tmp_path: Path):
    registry = PluginRegistry(tmp_path)
    manifest = {"id": "sample", "name": "Sample", "version": "1.0", "permissions": ["workspace.read"]}
    registry.install_manifest(manifest)
    assert registry.discover()[0].plugin_id == "sample"


def test_unknown_plugin_permission_is_rejected(tmp_path: Path):
    registry = PluginRegistry(tmp_path)
    folder = tmp_path / "unsafe"
    folder.mkdir()
    (folder / "plugin.json").write_text(
        json.dumps({"id": "unsafe", "name": "Unsafe", "version": "1", "permissions": ["root.access"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        registry.discover()


def _signed_package(tmp_path: Path, tamper: bool = False) -> tuple[Path, str]:
    import base64
    import hashlib
    import json
    import zipfile

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    manifest = {
        "id": "signed-sample",
        "name": "Signed Sample",
        "version": "1.0.0",
        "permissions": ["workspace.read"],
    }
    files = {
        "manifest.json": json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
        "README.md": b"Safe plugin package. Its code is not executed.",
    }
    signed_payload = {
        "manifest": manifest,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    canonical = json.dumps(signed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    private_key = Ed25519PrivateKey.generate()
    signature = private_key.sign(canonical)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if tamper:
        files["README.md"] = b"Modified after signing."
    package = tmp_path / "sample.fluxplugin"
    with zipfile.ZipFile(package, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("SIGNATURE.ed25519", base64.b64encode(signature))
    return package, base64.b64encode(public_key).decode()


def test_signed_plugin_package_verifies_and_installs_without_extracting_code(tmp_path: Path):
    pytest.importorskip("cryptography")
    package, public_key = _signed_package(tmp_path)
    destination = PluginRegistry(tmp_path / "registry").install_package(package, public_key)
    assert destination.is_file()
    assert destination.name == "1.0.0.fluxplugin"
    assert (destination.parent / "plugin.json").is_file()
    assert not (destination.parent / "README.md").exists()


def test_signed_plugin_package_rejects_tampering(tmp_path: Path):
    pytest.importorskip("cryptography")
    package, public_key = _signed_package(tmp_path, tamper=True)
    with pytest.raises(ValueError, match="signature verification failed"):
        PluginRegistry(tmp_path / "registry").install_package(package, public_key)


def test_signed_plugin_package_rejects_path_traversal(tmp_path: Path):
    import base64
    import zipfile

    pytest.importorskip("cryptography")
    package = tmp_path / "unsafe.fluxplugin"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../escape.txt", b"bad")
        archive.writestr("manifest.json", b"{}")
        archive.writestr("SIGNATURE.ed25519", base64.b64encode(b"x" * 64))
    with pytest.raises(ValueError, match="Unsafe or duplicate"):
        PluginRegistry(tmp_path / "registry").install_package(package, base64.b64encode(b"x" * 32).decode())


def test_signed_catalog_downloads_exact_package_and_verifies_both_signatures(tmp_path: Path, monkeypatch):
    pytest.importorskip("cryptography")
    import base64
    import hashlib
    import io
    import json
    import zipfile

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    manifest = {
        "id": "catalog-plugin",
        "name": "Catalog Plugin",
        "version": "2.0.0",
        "permissions": ["workspace.read"],
    }
    package_files = {
        "manifest.json": json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
        "README.md": b"Catalog package content.",
    }
    package_payload = {
        "manifest": manifest,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(package_files.items())},
    }
    private_key = Ed25519PrivateKey.generate()
    package_signature = private_key.sign(
        json.dumps(package_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    )
    package_stream = io.BytesIO()
    with zipfile.ZipFile(package_stream, "w") as archive:
        for name, data in package_files.items():
            archive.writestr(name, data)
        archive.writestr("SIGNATURE.ed25519", base64.b64encode(package_signature))
    package_bytes = package_stream.getvalue()
    catalog = {
        "schema_version": 1,
        "plugins": [{
            "id": manifest["id"],
            "version": manifest["version"],
            "url": "https://plugins.example/catalog-plugin.fluxplugin",
            "sha256": hashlib.sha256(package_bytes).hexdigest(),
        }],
    }
    catalog_signature = private_key.sign(
        json.dumps(catalog, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    )
    catalog["signature"] = base64.b64encode(catalog_signature).decode()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    class Response:
        def __init__(self, content: bytes, payload: dict | None = None):
            self.content = content
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, **_kwargs):
        if url == "https://plugins.example/catalog.json":
            body = json.dumps(catalog).encode()
            return Response(body, catalog)
        return Response(package_bytes)

    monkeypatch.setattr("httpx.get", fake_get)
    destination = PluginRegistry(tmp_path / "registry").install_from_catalog(
        "https://plugins.example/catalog.json",
        manifest["id"],
        manifest["version"],
        base64.b64encode(public_key).decode(),
    )
    assert destination.is_file()
    assert json.loads((destination.parent / "plugin.json").read_text())["id"] == manifest["id"]


def test_plugin_catalog_requires_https(tmp_path: Path):
    pytest.importorskip("cryptography")
    with pytest.raises(ValueError, match="HTTPS"):
        PluginRegistry(tmp_path / "registry").install_from_catalog(
            "http://plugins.example/catalog.json", "plugin", "1.0.0", "invalid"
        )


def test_plugin_package_builder_creates_verifiable_archive(tmp_path: Path):
    pytest.importorskip("cryptography")
    import base64
    import json

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from flux_agent.integrations.plugins import build_signed_package

    source = tmp_path / "source"
    source.mkdir()
    (source / "manifest.json").write_text(
        json.dumps({
            "id": "built-plugin",
            "name": "Built Plugin",
            "version": "1.0.0",
            "permissions": ["workspace.read"],
        }),
        encoding="utf-8",
    )
    (source / "README.md").write_text("Package metadata only.", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    package = build_signed_package(
        source,
        tmp_path / "built.fluxplugin",
        base64.b64encode(private_bytes).decode(),
    )
    installed = PluginRegistry(tmp_path / "registry").install_package(
        package, base64.b64encode(public_bytes).decode()
    )
    assert installed.is_file()
    assert installed.parent.name == "built-plugin"


def test_plugin_package_builder_rejects_output_inside_source(tmp_path: Path):
    import base64

    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from flux_agent.integrations.plugins import build_signed_package

    source = tmp_path / "source"
    source.mkdir()
    key = base64.b64encode(Ed25519PrivateKey.generate().private_bytes_raw()).decode()
    with pytest.raises(ValueError, match="outside"):
        build_signed_package(source, source / "output.fluxplugin", key)


def test_signed_plugin_package_rejects_windows_style_paths(tmp_path: Path):
    import base64
    import zipfile

    pytest.importorskip("cryptography")
    package = tmp_path / "windows-path.fluxplugin"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(r"..\\escape.txt", b"bad")
        archive.writestr("manifest.json", b"{}")
        archive.writestr("SIGNATURE.ed25519", base64.b64encode(b"x" * 64))
    with pytest.raises(ValueError, match="Unsafe or duplicate"):
        PluginRegistry(tmp_path / "registry").install_package(
            package, base64.b64encode(b"x" * 32).decode()
        )
