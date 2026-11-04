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
