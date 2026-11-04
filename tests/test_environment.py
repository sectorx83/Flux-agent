import json
import os
from pathlib import Path

import pytest

from flux_agent.environment import EnvironmentStore


def test_environment_store_round_trips_values_without_exposing_them(tmp_path: Path):
    path = tmp_path / "config" / "secrets.json"
    store = EnvironmentStore(path)
    store.set("GROQ_API_KEY", "secret-value")
    assert store.keys() == ["GROQ_API_KEY"]
    target = {}
    assert store.load_into(target) == ["GROQ_API_KEY"]
    assert target["GROQ_API_KEY"] == "secret-value"
    assert store.unset("GROQ_API_KEY") is True
    assert store.keys() == []


def test_environment_store_does_not_override_existing_process_environment(tmp_path: Path):
    store = EnvironmentStore(tmp_path / "secrets.json")
    store.set("GROQ_API_KEY", "stored")
    target = {"GROQ_API_KEY": "explicit"}
    assert store.load_into(target) == []
    assert target["GROQ_API_KEY"] == "explicit"


@pytest.mark.parametrize("key", ["lowercase", "BAD-KEY", "1INVALID", "PATH", "PYTHONPATH"])
def test_environment_store_rejects_invalid_or_protected_keys(tmp_path: Path, key: str):
    with pytest.raises(ValueError):
        EnvironmentStore(tmp_path / "secrets.json").set(key, "value")


def test_environment_store_rejects_corrupt_file_without_overwriting(tmp_path: Path):
    path = tmp_path / "secrets.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        EnvironmentStore(path).set("GROQ_API_KEY", "secret")
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_environment_store_uses_private_file_permissions_on_posix(tmp_path: Path):
    if os.name == "nt":
        pytest.skip("POSIX file permission bits are not available on Windows.")
    path = tmp_path / "secrets.json"
    EnvironmentStore(path).set("GROQ_API_KEY", "secret")
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
