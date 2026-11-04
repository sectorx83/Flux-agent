from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flux_agent.workflows.engine import WorkflowEngine


def test_due_workflow_runs_once(tmp_path: Path):
    engine = WorkflowEngine(tmp_path / "workflows.db")
    engine.add("backup", {"path": "."}, datetime.now(UTC) - timedelta(seconds=1))
    ran = []
    assert engine.run_due(lambda name, payload: ran.append((name, payload))) == 1
    assert ran == [("backup", {"path": "."})]
    assert engine.run_due(lambda *_: None) == 0


def test_failed_workflow_retries_then_disables(tmp_path: Path):
    engine = WorkflowEngine(tmp_path / "workflows.db")
    now = datetime.now(UTC)
    workflow_id = engine.add(
        "retry-me", {"task": "test"}, now - timedelta(seconds=1),
        max_retries=1, retry_delay_seconds=30,
    )
    assert engine.run_due(lambda *_: (_ for _ in ()).throw(RuntimeError("temporary")), now) == 0
    item = next(item for item in engine.list() if item["id"] == workflow_id)
    assert item["attempts"] == 1
    assert item["enabled"] == 1
    assert item["last_error"] == "temporary"
    assert engine.run_due(lambda *_: None, now + timedelta(seconds=31)) == 1
    item = next(item for item in engine.list() if item["id"] == workflow_id)
    assert item["enabled"] == 0
    assert item["last_error"] is None


def test_event_workflow_waits_for_trigger_and_can_be_reused(tmp_path: Path):
    engine = WorkflowEngine(tmp_path / "workflows.db")
    now = datetime.now(UTC)
    engine.add("on-push", {"task": "check"}, now - timedelta(days=1), event_name="git.push")
    ran = []
    assert engine.run_due(lambda name, payload: ran.append(name), now) == 0
    assert engine.trigger_event("git.push", now) == 1
    assert engine.run_due(lambda name, payload: ran.append(name), now) == 1
    assert ran == ["on-push"]
    assert engine.trigger_event("git.push", now + timedelta(seconds=1)) == 1
    assert engine.trigger_event("git.push", now + timedelta(seconds=2)) == 1
    assert engine.run_due(lambda name, payload: ran.append(name), now + timedelta(seconds=2)) == 1
    assert ran == ["on-push", "on-push"]
    assert engine.list()[0]["pending"] == 0
    assert engine.list()[0]["pending_count"] == 1
    assert engine.run_due(lambda name, payload: ran.append(name), now + timedelta(seconds=2)) == 1
    assert ran == ["on-push", "on-push", "on-push"]
    assert engine.list()[0]["pending"] == 1
    assert engine.list()[0]["pending_count"] == 0



def test_existing_workflow_database_is_migrated(tmp_path: Path):
    import sqlite3

    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """CREATE TABLE workflows (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL,
                run_at TEXT NOT NULL, interval_seconds INTEGER, enabled INTEGER NOT NULL DEFAULT 1
            )"""
        )
        db.execute(
            "INSERT INTO workflows(name,payload,run_at) VALUES(?,?,?)",
            ("legacy", '{"task":"check"}', datetime.now(UTC).isoformat()),
        )

    item = WorkflowEngine(path).list()[0]
    assert item["name"] == "legacy"
    assert item["attempts"] == 0
    assert item["max_retries"] == 0
    assert item["pending_count"] == 0


def test_workflow_rejects_naive_time_and_non_object_payload(tmp_path: Path):
    engine = WorkflowEngine(tmp_path / "workflows.db")
    with pytest.raises(ValueError, match="timezone"):
        engine.add("bad-time", {}, datetime.now())
    with pytest.raises(ValueError, match="JSON object"):
        engine.add("bad-payload", [], datetime.now(UTC))
