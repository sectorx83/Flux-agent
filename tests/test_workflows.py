from datetime import UTC, datetime, timedelta
from pathlib import Path

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
    assert engine.list()[0]["pending"] == 1
    assert engine.list()[0]["pending_count"] == 0
