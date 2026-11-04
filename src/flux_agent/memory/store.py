"""Persistent local project memory with SQLite full-text retrieval."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY, project TEXT NOT NULL, category TEXT NOT NULL,
                    content TEXT NOT NULL, created_at TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content, category, project, content='memories', content_rowid='id'
                )"""
            )
            db.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, category, project)
                    VALUES (new.id, new.content, new.category, new.project);
                END;
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, category, project)
                    VALUES ('delete', old.id, old.content, old.category, old.project);
                END;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add(self, project: str, content: str, category: str = "note") -> int:
        clean = content.strip()
        if not clean:
            raise ValueError("Memory content cannot be empty.")
        if len(clean) > 50_000:
            raise ValueError("Memory content exceeds the 50,000 character limit.")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO memories(project, category, content, created_at) VALUES (?, ?, ?, ?)",
                (project, category, clean, datetime.now(UTC).isoformat()),
            )
            return int(cursor.lastrowid)

    def search(self, project: str, query: str, limit: int = 8) -> list[dict[str, str | int]]:
        terms = [term for term in query.split() if term.isalnum()]
        if not terms:
            return []
        expression = " OR ".join(f'"{term}"' for term in terms[:12])
        with self._connect() as db:
            rows = db.execute(
                """SELECT m.id, m.category, m.content, m.created_at
                   FROM memories_fts f JOIN memories m ON m.id = f.rowid
                   WHERE memories_fts MATCH ? AND m.project = ?
                   ORDER BY bm25(memories_fts) LIMIT ?""",
                (expression, project, max(1, min(limit, 50))),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, memory_id: int, project: str) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM memories WHERE id = ? AND project = ?", (memory_id, project)
            )
            return cursor.rowcount > 0
