"""Per-device remote credentials with hashed token storage and revocation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RemoteDeviceStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS remote_devices (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL, last_used_at TEXT, revoked_at TEXT
                )"""
            )

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def pair(self, name: str) -> tuple[dict[str, Any], str]:
        clean = name.strip()
        if not clean or len(clean) > 80:
            raise ValueError("Device name must contain 1-80 characters.")
        device_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(48)
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO remote_devices(id,name,token_hash,created_at) VALUES(?,?,?,?)",
                (device_id, clean, self._hash(token), now),
            )
        return self.get(device_id), token

    def authenticate(self, token: str) -> str | None:
        if not token:
            return None
        supplied = self._hash(token)
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT id,token_hash FROM remote_devices WHERE revoked_at IS NULL"
            ).fetchall()
            for device_id, token_hash in rows:
                if hmac.compare_digest(supplied, token_hash):
                    db.execute(
                        "UPDATE remote_devices SET last_used_at=? WHERE id=?",
                        (datetime.now(UTC).isoformat(), device_id),
                    )
                    return str(device_id)
        return None

    def list(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT id,name,created_at,last_used_at,revoked_at FROM remote_devices ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, device_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT id,name,created_at,last_used_at,revoked_at FROM remote_devices WHERE id=?",
                (device_id,),
            ).fetchone()
        if row is None:
            raise KeyError(device_id)
        return dict(row)

    def revoke(self, device_id: str) -> bool:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "UPDATE remote_devices SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
                (datetime.now(UTC).isoformat(), device_id),
            )
            return cursor.rowcount > 0
