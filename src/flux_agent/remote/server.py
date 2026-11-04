"""Optional authenticated remote control API. Bind to loopback or a private VPN interface."""

from __future__ import annotations

import hmac
import os


def create_app():
    try:
        from fastapi import FastAPI, Header, HTTPException
        from pydantic import BaseModel
    except ImportError as exc:
        raise RuntimeError("Install remote support with: pip install 'flux-agent[remote]'") from exc

    token = os.getenv("FLUX_REMOTE_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set FLUX_REMOTE_TOKEN to a random value of at least 32 characters.")

    class TaskRequest(BaseModel):
        prompt: str
        mode: str = "chat"

    app = FastAPI(title="Flux Agent Remote API", version="0.1.0")
    tasks: list[dict] = []

    def authorize(authorization: str | None) -> None:
        supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if not hmac.compare_digest(supplied, token):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "flux-agent"}

    @app.post("/tasks")
    def create_task(request: TaskRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if request.mode not in {"chat", "plan", "build"}:
            raise HTTPException(status_code=400, detail="Invalid mode")
        if not request.prompt.strip() or len(request.prompt) > 20_000:
            raise HTTPException(status_code=400, detail="Prompt must contain 1-20000 characters")
        task = {"id": len(tasks) + 1, "mode": request.mode, "prompt": request.prompt, "status": "queued"}
        tasks.append(task)
        return task

    @app.get("/tasks")
    def list_tasks(authorization: str | None = Header(default=None)):
        authorize(authorization)
        return {"tasks": tasks[-100:]}

    return app
