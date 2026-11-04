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
