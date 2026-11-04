"""Authenticated remote API with per-device access and task streaming."""

from __future__ import annotations

import hmac
import json
import os
import time
from pathlib import Path

from flux_agent.remote.devices import RemoteDeviceStore


def create_app():
    try:
        from fastapi import FastAPI, Header, HTTPException
        from fastapi.responses import StreamingResponse
        from platformdirs import user_data_dir
    except ImportError as exc:
        raise RuntimeError("Install remote support with: pip install 'flux-agent[remote]'") from exc

    from flux_agent.remote.tasks import RemoteTaskStore

    admin_token = os.getenv("FLUX_REMOTE_TOKEN", "")
    if len(admin_token) < 32:
        raise RuntimeError("Set FLUX_REMOTE_TOKEN to a random value of at least 32 characters.")
    data_dir = Path(user_data_dir("flux-agent"))
    task_path = Path(os.getenv("FLUX_REMOTE_DB", str(data_dir / "remote-tasks.sqlite3")))
    device_path = Path(os.getenv("FLUX_REMOTE_DEVICE_DB", str(data_dir / "remote-devices.sqlite3")))
    tasks = RemoteTaskStore(task_path)
    devices = RemoteDeviceStore(device_path)

    app = FastAPI(title="Flux Agent Remote API", version="0.3.0")

    def authenticate(authorization: str | None) -> str:
        supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if hmac.compare_digest(supplied, admin_token):
            return "admin"
        device_id = devices.authenticate(supplied)
        if device_id:
            return device_id
        raise HTTPException(status_code=401, detail="Unauthorized")

    def authorize_admin(authorization: str | None) -> None:
        if authenticate(authorization) != "admin":
            raise HTTPException(status_code=403, detail="Administrator credential required.")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "flux-agent"}

    @app.post("/devices/pair")
    def pair_device(request: dict, authorization: str | None = Header(default=None)):
        authorize_admin(authorization)
        device_name = request.get("device_name")
        if not isinstance(device_name, str) or not device_name.strip() or len(device_name.strip()) > 80:
            raise HTTPException(status_code=400, detail="Device name must contain 1-80 characters.")
        try:
            device, token = devices.pair(device_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"device": device, "token": token, "warning": "Save this token now. It cannot be retrieved later."}

    @app.get("/devices")
    def list_devices(authorization: str | None = Header(default=None)):
        authorize_admin(authorization)
        return {"devices": devices.list()}

    @app.delete("/devices/{device_id}")
    def revoke_device(device_id: str, authorization: str | None = Header(default=None)):
        authorize_admin(authorization)
        if not devices.revoke(device_id):
            raise HTTPException(status_code=404, detail="Active device not found.")
        return {"device_id": device_id, "revoked": True}

    @app.post("/tasks")
    def create_task(request: dict, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization)
        prompt = request.get("prompt")
        mode = request.get("mode", "chat")
        if not isinstance(mode, str) or mode not in {"chat", "plan", "build"}:
            raise HTTPException(status_code=400, detail="Invalid mode")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
            raise HTTPException(status_code=400, detail="Prompt must contain 1-20000 characters")
        task = tasks.enqueue(prompt, mode, identity)
        task.pop("device_id", None)
        return task

    @app.get("/tasks")
    def list_tasks(authorization: str | None = Header(default=None)):
        identity = authenticate(authorization)
        records = tasks.list(limit=100, device_id=None if identity == "admin" else identity)
        for task in records:
            task.pop("device_id", None)
        return {"tasks": records}

    def get_authorized_task(task_id: int, identity: str):
        try:
            return tasks.get(task_id, device_id=None if identity == "admin" else identity)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found.") from exc

    @app.get("/tasks/{task_id}")
    def get_task(task_id: int, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization)
        task = get_authorized_task(task_id, identity)
        task.pop("device_id", None)
        return task

    @app.get("/tasks/{task_id}/stream")
    def stream_task(task_id: int, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization)
        get_authorized_task(task_id, identity)

        def events():
            previous = None
            deadline = time.monotonic() + 3600
            while time.monotonic() < deadline:
                task = get_authorized_task(task_id, identity)
                state = {
                    "id": task["id"], "status": task["status"], "result": task["result"],
                    "error": task["error"], "updated_at": task["updated_at"],
                }
                encoded = json.dumps(state, separators=(",", ":"))
                if encoded != previous:
                    yield f"event: update\ndata: {encoded}\n\n"
                    previous = encoded
                if task["status"] in {"completed", "failed"}:
                    yield "event: complete\ndata: {}\n\n"
                    return
                yield ": keep-alive\n\n"
                time.sleep(1)
            yield "event: timeout\ndata: {}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/workflows/events/{event_name}")
    def trigger_workflows(event_name: str, authorization: str | None = Header(default=None)):
        authorize_admin(authorization)
        from flux_agent.workflows.engine import WorkflowEngine

        engine = WorkflowEngine(data_dir / "workflows.sqlite3")
        try:
            count = engine.trigger_event(event_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"event": event_name, "triggered": count}

    return app
