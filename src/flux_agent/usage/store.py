"""Local token-usage and optional model-cost accounting."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class UsageStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL, completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL, estimated_cost REAL, created_at TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS model_prices (
                    model TEXT PRIMARY KEY, input_per_million REAL NOT NULL,
                    output_per_million REAL NOT NULL, updated_at TEXT NOT NULL
                )"""
            )

    def set_price(self, model: str, input_per_million: float, output_per_million: float) -> None:
        if not model.strip():
            raise ValueError("Model name cannot be empty.")
        if input_per_million < 0 or output_per_million < 0:
            raise ValueError("Token prices cannot be negative.")
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO model_prices(model,input_per_million,output_per_million,updated_at)
                   VALUES(?,?,?,?) ON CONFLICT(model) DO UPDATE SET
                   input_per_million=excluded.input_per_million,
                   output_per_million=excluded.output_per_million,updated_at=excluded.updated_at""",
                (model, input_per_million, output_per_million, now),
            )

    def record(self, provider: str, model: str, usage: dict[str, Any]) -> None:
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", prompt + completion) or prompt + completion)
        if min(prompt, completion, total) < 0 or total < prompt + completion:
            raise ValueError("Provider returned invalid token usage values.")
        with sqlite3.connect(self.path) as db:
            price = db.execute(
                "SELECT input_per_million,output_per_million FROM model_prices WHERE model=?",
                (model,),
            ).fetchone()
            cost = None
            if price is not None:
                cost = (prompt * price[0] + completion * price[1]) / 1_000_000
            db.execute(
                """INSERT INTO usage_events(
                    provider,model,prompt_tokens,completion_tokens,total_tokens,estimated_cost,created_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (provider, model, prompt, completion, total, cost, datetime.now(UTC).isoformat()),
            )

    def summary(self, limit: int = 100) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """SELECT provider,model,COUNT(*) AS requests,
                   SUM(prompt_tokens) AS prompt_tokens,
                   SUM(completion_tokens) AS completion_tokens,
                   SUM(total_tokens) AS total_tokens,
                   CASE WHEN COUNT(estimated_cost)=0 THEN NULL ELSE SUM(estimated_cost) END AS estimated_cost
                   FROM usage_events GROUP BY provider,model ORDER BY total_tokens DESC LIMIT ?""",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def totals(self) -> dict[str, Any]:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                """SELECT COUNT(*),COALESCE(SUM(prompt_tokens),0),
                   COALESCE(SUM(completion_tokens),0),COALESCE(SUM(total_tokens),0),
                   CASE WHEN COUNT(estimated_cost)=0 THEN NULL ELSE SUM(estimated_cost) END
                   FROM usage_events"""
            ).fetchone()
        return {
            "requests": row[0], "prompt_tokens": row[1], "completion_tokens": row[2],
            "total_tokens": row[3], "estimated_cost": row[4],
        }
