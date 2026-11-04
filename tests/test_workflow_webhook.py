import pytest

from flux_agent.remote.server import create_app
from flux_agent.workflows.engine import WorkflowEngine


def test_authenticated_webhook_triggers_waiting_workflow(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import platformdirs

    monkeypatch.setenv("FLUX_REMOTE_TOKEN", "t" * 48)
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda _name: str(tmp_path))
    engine = WorkflowEngine(tmp_path / "workflows.sqlite3")
    from datetime import UTC, datetime

    engine.add("on-push", {"task": "check"}, datetime.now(UTC), event_name="git.push")
    client = TestClient(create_app())

    unauthorized = client.post("/workflows/events/git.push")
    assert unauthorized.status_code == 401

    response = client.post(
        "/workflows/events/git.push",
        headers={"Authorization": f"Bearer {'t' * 48}"},
    )
    assert response.status_code == 200
    assert response.json() == {"event": "git.push", "triggered": 1}
    assert engine.list()[0]["pending"] == 0
