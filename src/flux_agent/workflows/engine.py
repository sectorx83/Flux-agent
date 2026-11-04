"""Local persistent one-shot and interval workflow scheduler."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path


class WorkflowEngine:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL,
                    run_at TEXT NOT NULL, interval_seconds INTEGER, enabled INTEGER NOT NULL DEFAULT 1
                )"""
            )

    def add(
        self, name: str, payload: dict, run_at: datetime, interval_seconds: int | None = None
    ) -> int:
        if interval_seconds is not None and interval_seconds < 60:
            raise ValueError("Recurring workflows must have an interval of at least 60 seconds.")
        when = run_at.astimezone(UTC)
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "INSERT INTO workflows(name,payload,run_at,interval_seconds) VALUES(?,?,?,?)",
                (name, json.dumps(payload), when.isoformat(), interval_seconds),
            )
            return int(cursor.lastrowid)

    def list(self) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM workflows ORDER BY run_at").fetchall()
        return [dict(row) for row in rows]

    def run_due(self, handler: Callable[[str, dict], None], now: datetime | None = None) -> int:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        completed = 0
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            due = db.execute(
                "SELECT * FROM workflows WHERE enabled=1 AND run_at<=? ORDER BY run_at",
                (current.isoformat(),),
            ).fetchall()
            for item in due:
                handler(item["name"], json.loads(item["payload"]))
                if item["interval_seconds"]:
                    next_run = current + timedelta(seconds=item["interval_seconds"])
                    db.execute(
                        "UPDATE workflows SET run_at=? WHERE id=?",
                        (next_run.isoformat(), item["id"]),
                    )
                else:
                    db.execute("UPDATE workflows SET enabled=0 WHERE id=?", (item["id"],))
                completed += 1
        return completed

    def cancel(self, workflow_id: int) -> bool:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("UPDATE workflows SET enabled=0 WHERE id=?", (workflow_id,))
            return cursor.rowcount > 0
