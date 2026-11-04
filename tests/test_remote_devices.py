from pathlib import Path

from flux_agent.remote.devices import RemoteDeviceStore


def test_device_pairing_stores_only_hash_and_authenticates_token(tmp_path: Path):
    store = RemoteDeviceStore(tmp_path / "devices.db")
    device, token = store.pair("Android phone")
    assert device["name"] == "Android phone"
    assert token not in str(device)
    assert store.authenticate(token) == device["id"]
    assert store.get(device["id"])["last_used_at"] is not None


def test_device_revocation_invalidates_token(tmp_path: Path):
    store = RemoteDeviceStore(tmp_path / "devices.db")
    device, token = store.pair("Laptop")
    assert store.revoke(device["id"])
    assert store.authenticate(token) is None
    assert store.get(device["id"])["revoked_at"] is not None


def test_device_name_validation(tmp_path: Path):
    import pytest

    store = RemoteDeviceStore(tmp_path / "devices.db")
    with pytest.raises(ValueError, match="1-80"):
        store.pair(" ")
