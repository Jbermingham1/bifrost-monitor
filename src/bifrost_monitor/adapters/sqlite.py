"""SQLite storage adapter — zero-config local persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bifrost_monitor.models.run import RunFilter, RunRecord, RunStatus, TokenUsage

_DEFAULT_DB_PATH = Path.home() / ".bifrost-monitor" / "runs.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'success',
    started_at TEXT NOT NULL,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    error_type TEXT,
    error_message TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_runs_name ON runs(name);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
"""


class SQLiteStore:
    """Local SQLite run storage."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(_CREATE_TABLE)
        cursor.executescript(_CREATE_INDEX)
        self._conn.commit()

    def save(self, record: RunRecord) -> None:
        """Save a run record."""
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO runs
               (id, name, model, status, started_at, duration_ms,
                input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
                cost_usd, error_type, error_message, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.name,
                record.model,
                record.status.value,
                record.started_at.isoformat(),
                record.duration_ms,
                record.token_usage.input_tokens,
                record.token_usage.output_tokens,
                record.token_usage.cache_read_tokens,
                record.token_usage.cache_creation_tokens,
                record.cost_usd,
                record.error_type,
                record.error_message,
                json.dumps(record.metadata),
            ),
        )
        self._conn.commit()

    def query(self, **kwargs: Any) -> list[RunRecord]:
        """Query runs with optional filters."""
        run_filter = RunFilter(**kwargs) if kwargs else RunFilter()
        return self.query_filter(run_filter)

    def query_filter(self, run_filter: RunFilter) -> list[RunRecord]:
        """Query runs using a RunFilter object."""
        conditions: list[str] = []
        params: list[Any] = []

        if run_filter.name is not None:
            conditions.append("name = ?")
            params.append(run_filter.name)

        if run_filter.model is not None:
            conditions.append("model = ?")
            params.append(run_filter.model)

        if run_filter.status is not None:
            conditions.append("status = ?")
            params.append(run_filter.status.value)

        since = run_filter.get_since()
        if since is not None:
            conditions.append("started_at >= ?")
            params.append(since.isoformat())

        if run_filter.until is not None:
            conditions.append("started_at <= ?")
            params.append(run_filter.until.isoformat())

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM runs WHERE {where} ORDER BY started_at DESC LIMIT ?"  # noqa: S608  # nosec B608 - where clause built from hardcoded column names, all values parameterized
        params.append(run_filter.limit)

        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [self._row_to_record(row) for row in rows]

    def count(self) -> int:
        """Count total runs."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runs")
        result = cursor.fetchone()
        return int(result[0]) if result else 0

    def delete_all(self) -> None:
        """Delete all runs (useful for testing)."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM runs")
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> RunRecord:
        """Convert a database row to a RunRecord."""
        return RunRecord(
            id=row["id"],
            name=row["name"],
            model=row["model"],
            status=RunStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]).replace(tzinfo=UTC),
            duration_ms=row["duration_ms"],
            token_usage=TokenUsage(
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cache_read_tokens=row["cache_read_tokens"],
                cache_creation_tokens=row["cache_creation_tokens"],
            ),
            cost_usd=row["cost_usd"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            metadata=json.loads(row["metadata"]),
        )
