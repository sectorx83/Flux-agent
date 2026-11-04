from pathlib import Path

import pytest

from flux_agent.remote.client import RemoteClient
from flux_agent.remote.tasks import RemoteTaskStore


def test_remote_client_rejects_plain_http():
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteClient("http://localhost:8765", "x" * 48)


def test_remote_client_requires_long_token():
    with pytest.raises(ValueError, match="32 characters"):
        RemoteClient("https://example.invalid", "short")


def test_remote_tasks_are_scoped_to_device(tmp_path: Path):
    store = RemoteTaskStore(tmp_path / "tasks.db")
    first = store.enqueue("task one", "plan", "device-one")
    second = store.enqueue("task two", "chat", "device-two")
    assert [item["id"] for item in store.list(device_id="device-one")] == [first["id"]]
    with pytest.raises(KeyError):
        store.get(second["id"], device_id="device-one")
    assert store.get(second["id"], device_id="device-two")["prompt"] == "task two"


def test_remote_task_database_migrates_legacy_rows(tmp_path: Path):
    import sqlite3
    from datetime import UTC, datetime

    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """CREATE TABLE remote_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT NOT NULL, mode TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued', result TEXT, error TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        now = datetime.now(UTC).isoformat()
        db.execute(
            "INSERT INTO remote_tasks(prompt,mode,created_at,updated_at) VALUES(?,?,?,?)",
            ("legacy task", "plan", now, now),
        )
    task = RemoteTaskStore(path).get(1)
    assert task["device_id"] == "admin"
