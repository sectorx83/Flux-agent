from datetime import datetime, timedelta, timezone
from pathlib import Path

from flux_agent.workflows.engine import WorkflowEngine


def test_due_workflow_runs_once(tmp_path: Path):
    engine = WorkflowEngine(tmp_path / "workflows.db")
    engine.add("backup", {"path": "."}, datetime.now(timezone.utc) - timedelta(seconds=1))
    ran = []
    assert engine.run_due(lambda name, payload: ran.append((name, payload))) == 1
    assert ran == [("backup", {"path": "."})]
    assert engine.run_due(lambda *_: None) == 0
