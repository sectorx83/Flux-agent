"""Persistent local project memory with keyword and vector retrieval."""

from __future__ import annotations

import math
import sqlite3
import struct
from collections.abc import Sequence
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
            db.execute(
                """CREATE TABLE IF NOT EXISTS memory_embeddings (
                    memory_id INTEGER PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
                    model TEXT NOT NULL, dimensions INTEGER NOT NULL, vector BLOB NOT NULL
                )"""
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS memory_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
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
            rebuilt = db.execute(
                "SELECT value FROM memory_metadata WHERE key='fts_rebuilt'"
            ).fetchone()
            if rebuilt is None:
                db.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
                db.execute(
                    "INSERT INTO memory_metadata(key,value) VALUES('fts_rebuilt','1')"
                )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def add(self, project: str, content: str, category: str = "note") -> int:
        clean = content.strip()
        if not clean:
            raise ValueError("Memory content cannot be empty.")
        if len(clean) > 50_000:
            raise ValueError("Memory content exceeds the 50,000 character limit.")
        if not project.strip() or not category.strip():
            raise ValueError("Project and category cannot be empty.")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO memories(project, category, content, created_at) VALUES (?, ?, ?, ?)",
                (project, category, clean, datetime.now(UTC).isoformat()),
            )
            return int(cursor.lastrowid)

    def set_embedding(self, memory_id: int, project: str, model: str, vector: Sequence[float]) -> None:
        values = [float(value) for value in vector]
        if not values or len(values) > 16_384 or not all(math.isfinite(value) for value in values):
            raise ValueError("Embedding vector is empty, too large, or contains non-finite values.")
        blob = struct.pack(f"<{len(values)}f", *values)
        with self._connect() as db:
            exists = db.execute(
                "SELECT 1 FROM memories WHERE id=? AND project=?", (memory_id, project)
            ).fetchone()
            if exists is None:
                raise KeyError(memory_id)
            db.execute(
                """INSERT INTO memory_embeddings(memory_id,model,dimensions,vector) VALUES(?,?,?,?)
                   ON CONFLICT(memory_id) DO UPDATE SET
                   model=excluded.model,dimensions=excluded.dimensions,vector=excluded.vector""",
                (memory_id, model, len(values), blob),
            )

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

    def search_semantic(
        self, project: str, query_vector: Sequence[float], model: str, limit: int = 8
    ) -> list[dict[str, str | int | float]]:
        query = [float(value) for value in query_vector]
        if not query or not all(math.isfinite(value) for value in query):
            raise ValueError("Query embedding must contain finite values.")
        query_norm = math.sqrt(sum(value * value for value in query))
        if query_norm == 0:
            raise ValueError("Query embedding cannot be a zero vector.")
        with self._connect() as db:
            rows = db.execute(
                """SELECT m.id,m.category,m.content,m.created_at,e.dimensions,e.vector
                   FROM memories m JOIN memory_embeddings e ON e.memory_id=m.id
                   WHERE m.project=? AND e.model=? AND e.dimensions=?""",
                (project, model, len(query)),
            ).fetchall()
        ranked = []
        for row in rows:
            vector = struct.unpack(f"<{row['dimensions']}f", row["vector"])
            norm = math.sqrt(sum(value * value for value in vector))
            if norm == 0:
                continue
            score = sum(a * b for a, b in zip(query, vector, strict=True)) / (query_norm * norm)
            ranked.append(
                {
                    "id": row["id"], "category": row["category"], "content": row["content"],
                    "created_at": row["created_at"], "score": score,
                }
            )
        ranked.sort(key=lambda item: float(item["score"]), reverse=True)
        return ranked[: max(1, min(limit, 50))]

    def list_unembedded(self, project: str, model: str, limit: int = 100) -> list[dict[str, str | int]]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT m.id,m.content FROM memories m
                   LEFT JOIN memory_embeddings e ON e.memory_id=m.id
                   WHERE m.project=? AND (e.memory_id IS NULL OR e.model<>?)
                   ORDER BY m.id LIMIT ?""",
                (project, model, max(1, min(limit, 500))),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, memory_id: int, project: str) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM memories WHERE id = ? AND project = ?", (memory_id, project)
            )
            return cursor.rowcount > 0
