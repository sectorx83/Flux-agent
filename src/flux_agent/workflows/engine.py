"""Persistent scheduler with retries and named event-triggered workflows."""

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
            columns = {row[1] for row in db.execute("PRAGMA table_info(workflows)")}
            migrations = {
                "attempts": "INTEGER NOT NULL DEFAULT 0",
                "max_retries": "INTEGER NOT NULL DEFAULT 0",
                "retry_delay_seconds": "INTEGER NOT NULL DEFAULT 60",
                "last_error": "TEXT",
                "event_name": "TEXT",
                "pending": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, declaration in migrations.items():
                if column not in columns:
                    db.execute(f"ALTER TABLE workflows ADD COLUMN {column} {declaration}")

    def add(
        self,
        name: str,
        payload: dict,
        run_at: datetime,
        interval_seconds: int | None = None,
        max_retries: int = 0,
        retry_delay_seconds: int = 60,
        event_name: str | None = None,
    ) -> int:
        if not name.strip():
            raise ValueError("Workflow name cannot be empty.")
        if not isinstance(payload, dict):
            raise ValueError("Workflow payload must be a JSON object.")
        if run_at.tzinfo is None or run_at.utcoffset() is None:
            raise ValueError("Workflow run_at must include a timezone.")
        if event_name is not None:
            event_name = event_name.strip()
        if interval_seconds is not None and interval_seconds < 60:
            raise ValueError("Recurring workflows must have an interval of at least 60 seconds.")
        if max_retries < 0 or max_retries > 20:
            raise ValueError("max_retries must be between 0 and 20.")
        if retry_delay_seconds < 1 or retry_delay_seconds > 86400:
            raise ValueError("retry_delay_seconds must be between 1 and 86400.")
        if event_name is not None and (not event_name.strip() or interval_seconds is not None):
            raise ValueError("Event workflows need a non-empty event name and cannot also repeat on an interval.")
        when = run_at.astimezone(UTC)
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                """INSERT INTO workflows(
                    name,payload,run_at,interval_seconds,max_retries,retry_delay_seconds,event_name,pending
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    name, json.dumps(payload), when.isoformat(), interval_seconds,
                    max_retries, retry_delay_seconds, event_name, int(event_name is not None),
                ),
            )
            return int(cursor.lastrowid)

    def list(self) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM workflows ORDER BY run_at").fetchall()
        return [dict(row) for row in rows]

    def trigger_event(self, event_name: str, now: datetime | None = None) -> int:
        if not event_name.strip():
            raise ValueError("Event name cannot be empty.")
        event_name = event_name.strip()
        current = (now or datetime.now(UTC)).astimezone(UTC)
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                """UPDATE workflows SET pending=0, run_at=?, attempts=0, last_error=NULL
                   WHERE enabled=1 AND pending=1 AND event_name=?""",
                (current.isoformat(), event_name),
            )
            return cursor.rowcount

    def run_due(
        self,
        handler: Callable[[str, dict], None],
        now: datetime | None = None,
        on_error: Callable[[str, Exception, bool], None] | None = None,
    ) -> int:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        completed = 0
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            due = db.execute(
                "SELECT * FROM workflows WHERE enabled=1 AND pending=0 AND run_at<=? ORDER BY run_at",
                (current.isoformat(),),
            ).fetchall()
            for item in due:
                try:
                    handler(item["name"], json.loads(item["payload"]))
                except Exception as exc:
                    attempts = int(item["attempts"]) + 1
                    error = str(exc)[:4000]
                    retrying = attempts <= int(item["max_retries"])
                    if retrying:
                        retry_at = current + timedelta(seconds=int(item["retry_delay_seconds"]))
                        db.execute(
                            "UPDATE workflows SET attempts=?, last_error=?, run_at=? WHERE id=?",
                            (attempts, error, retry_at.isoformat(), item["id"]),
                        )
                    else:
                        db.execute(
                            "UPDATE workflows SET attempts=?, last_error=?, enabled=0 WHERE id=?",
                            (attempts, error, item["id"]),
                        )
                    if on_error is not None:
                        on_error(item["name"], exc, retrying)
                    continue
                if item["event_name"]:
                    db.execute(
                        "UPDATE workflows SET pending=1, attempts=0, last_error=NULL WHERE id=?",
                        (item["id"],),
                    )
                elif item["interval_seconds"]:
                    next_run = current + timedelta(seconds=item["interval_seconds"])
                    db.execute(
                        "UPDATE workflows SET run_at=?, attempts=0, last_error=NULL WHERE id=?",
                        (next_run.isoformat(), item["id"]),
                    )
                else:
                    db.execute(
                        "UPDATE workflows SET enabled=0, attempts=0, last_error=NULL WHERE id=?",
                        (item["id"],),
                    )
                completed += 1
        return completed

    def cancel(self, workflow_id: int) -> bool:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("UPDATE workflows SET enabled=0 WHERE id=?", (workflow_id,))
            return cursor.rowcount > 0
