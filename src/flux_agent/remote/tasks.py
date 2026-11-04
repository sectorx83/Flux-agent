"""Persistent SQLite queue for authenticated remote Flux tasks."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RemoteTaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS remote_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    device_id TEXT NOT NULL DEFAULT 'admin'
                )"""
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(remote_tasks)")}
            if "device_id" not in columns:
                db.execute(
                    "ALTER TABLE remote_tasks ADD COLUMN device_id TEXT NOT NULL DEFAULT 'admin'"
                )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def enqueue(self, prompt: str, mode: str, device_id: str = "admin") -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO remote_tasks(prompt,mode,created_at,updated_at,device_id) VALUES(?,?,?,?,?)",
                (prompt, mode, now, now, device_id),
            )
            task_id = int(cursor.lastrowid)
        return self.get(task_id)

    def get(self, task_id: int, device_id: str | None = None) -> dict[str, Any]:
        with self._connect() as db:
            if device_id is None:
                row = db.execute("SELECT * FROM remote_tasks WHERE id=?", (task_id,)).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM remote_tasks WHERE id=? AND device_id=?",
                    (task_id, device_id),
                ).fetchone()
        if row is None:
            raise KeyError(task_id)
        return dict(row)

    def list(self, limit: int = 100, device_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if device_id is None:
                rows = db.execute(
                    "SELECT * FROM remote_tasks ORDER BY id DESC LIMIT ?",
                    (max(1, min(limit, 500)),),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM remote_tasks WHERE device_id=? ORDER BY id DESC LIMIT ?",
                    (device_id, max(1, min(limit, 500))),
                ).fetchall()
        return [dict(row) for row in rows]

    def claim_next(self) -> dict[str, Any] | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM remote_tasks WHERE status='queued' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            now = datetime.now(UTC).isoformat()
            db.execute(
                "UPDATE remote_tasks SET status='running',updated_at=? WHERE id=? AND status='queued'",
                (now, row['id']),
            )
            return dict(db.execute("SELECT * FROM remote_tasks WHERE id=?", (row['id'],)).fetchone())

    def complete(self, task_id: int, result: str) -> None:
        self._update(task_id, "completed", result=result, error=None)

    def fail(self, task_id: int, error: str) -> None:
        self._update(task_id, "failed", result=None, error=error[:10_000])

    def _update(self, task_id: int, status: str, result: str | None, error: str | None) -> None:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE remote_tasks SET status=?,result=?,error=?,updated_at=? WHERE id=?",
                (status, result, error, datetime.now(UTC).isoformat(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(task_id)
