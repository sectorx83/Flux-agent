from pathlib import Path

from flux_agent.remote.tasks import RemoteTaskStore


def test_remote_tasks_persist_and_complete(tmp_path: Path):
    path = tmp_path / "remote.db"
    store = RemoteTaskStore(path)
    created = store.enqueue("inspect project", "plan")
    assert created["status"] == "queued"

    reopened = RemoteTaskStore(path)
    claimed = reopened.claim_next()
    assert claimed["id"] == created["id"]
    assert claimed["status"] == "running"
    assert reopened.claim_next() is None

    reopened.complete(created["id"], "Project looks healthy")
    final = reopened.get(created["id"])
    assert final["status"] == "completed"
    assert final["result"] == "Project looks healthy"


def test_remote_task_failure_is_recorded(tmp_path: Path):
    store = RemoteTaskStore(tmp_path / "remote.db")
    task = store.enqueue("bad task", "chat")
    store.fail(task["id"], "provider unavailable")
    assert store.get(task["id"])["error"] == "provider unavailable"
