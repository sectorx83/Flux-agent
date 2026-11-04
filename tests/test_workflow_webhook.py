import pytest

from flux_agent.remote.server import create_app
from flux_agent.remote.tasks import RemoteTaskStore
from flux_agent.workflows.engine import WorkflowEngine


def _client(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    import platformdirs
    from fastapi.testclient import TestClient

    monkeypatch.setenv("FLUX_REMOTE_TOKEN", "t" * 48)
    monkeypatch.setenv("FLUX_REMOTE_DB", str(tmp_path / "tasks.sqlite3"))
    monkeypatch.setenv("FLUX_REMOTE_DEVICE_DB", str(tmp_path / "devices.sqlite3"))
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda _name: str(tmp_path))
    return TestClient(create_app())


def test_authenticated_webhook_triggers_waiting_workflow(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    engine = WorkflowEngine(tmp_path / "workflows.sqlite3")
    engine.add("on-push", {"task": "check"}, datetime.now(UTC), event_name="git.push")
    client = _client(tmp_path, monkeypatch)

    unauthorized = client.post("/workflows/events/git.push")
    assert unauthorized.status_code == 401

    response = client.post(
        "/workflows/events/git.push",
        headers={"Authorization": f"Bearer {'t' * 48}"},
    )
    assert response.status_code == 200
    assert response.json() == {"event": "git.push", "triggered": 1}
    assert engine.list()[0]["pending"] == 0


def test_device_pairing_task_isolation_and_revocation(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    admin = {"Authorization": f"Bearer {'t' * 48}"}

    paired_a = client.post("/devices/pair", json={"device_name": "Phone"}, headers=admin)
    paired_b = client.post("/devices/pair", json={"device_name": "Tablet"}, headers=admin)
    assert paired_a.status_code == paired_b.status_code == 200
    token_a = paired_a.json()["token"]
    token_b = paired_b.json()["token"]
    device_a = paired_a.json()["device"]["id"]
    assert token_a not in str(paired_a.json()["device"])

    response_a = client.post(
        "/tasks", json={"prompt": "private A", "mode": "plan"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    response_b = client.post(
        "/tasks", json={"prompt": "private B", "mode": "chat"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response_a.status_code == response_b.status_code == 200
    task_a = response_a.json()["id"]
    task_b = response_b.json()["id"]

    own_tasks = client.get("/tasks", headers={"Authorization": f"Bearer {token_a}"})
    assert [task["id"] for task in own_tasks.json()["tasks"]] == [task_a]
    assert client.get(f"/tasks/{task_b}", headers={"Authorization": f"Bearer {token_a}"}).status_code == 404
    assert len(client.get("/tasks", headers=admin).json()["tasks"]) == 2

    assert client.get("/devices", headers={"Authorization": f"Bearer {token_a}"}).status_code == 403
    revoked = client.delete(f"/devices/{device_a}", headers=admin)
    assert revoked.status_code == 200
    assert client.get("/tasks", headers={"Authorization": f"Bearer {token_a}"}).status_code == 401


def test_remote_task_stream_emits_terminal_state(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    admin = {"Authorization": f"Bearer {'t' * 48}"}
    created = client.post("/tasks", json={"prompt": "stream me", "mode": "plan"}, headers=admin)
    task_id = created.json()["id"]
    store = RemoteTaskStore(tmp_path / "tasks.sqlite3")
    store.complete(task_id, "finished")
    response = client.get(f"/tasks/{task_id}/stream", headers=admin)
    assert response.status_code == 200
    assert "event: update" in response.text
    assert '"status":"completed"' in response.text
    assert '"result":"finished"' in response.text
