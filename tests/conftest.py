"""Shared fixtures for bifrost-monitor tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from bifrost_monitor.adapters.sqlite import SQLiteStore
from bifrost_monitor.core.tracker import MonitorTracker
from bifrost_monitor.models.run import RunRecord, RunStatus, TokenUsage

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def store(tmp_db: Path) -> Generator[SQLiteStore, None, None]:
    """SQLiteStore with temporary database."""
    s = SQLiteStore(db_path=tmp_db)
    yield s
    s.close()


@pytest.fixture
def tracker(store: SQLiteStore) -> MonitorTracker:
    """MonitorTracker backed by temp SQLite store."""
    return MonitorTracker(store=store)


@pytest.fixture
def sample_records() -> list[RunRecord]:
    """Sample records for testing."""
    return [
        RunRecord(
            id="r1",
            name="support-agent",
            model="claude-sonnet-4-6",
            status=RunStatus.SUCCESS,
            started_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
            duration_ms=1500.0,
            token_usage=TokenUsage(input_tokens=500, output_tokens=200),
            cost_usd=0.0045,
        ),
        RunRecord(
            id="r2",
            name="triage-agent",
            model="gpt-4o",
            status=RunStatus.SUCCESS,
            started_at=datetime(2025, 6, 1, 13, 0, tzinfo=UTC),
            duration_ms=800.0,
            token_usage=TokenUsage(input_tokens=300, output_tokens=100),
            cost_usd=0.0018,
        ),
        RunRecord(
            id="r3",
            name="support-agent",
            model="claude-sonnet-4-6",
            status=RunStatus.ERROR,
            started_at=datetime(2025, 6, 1, 14, 0, tzinfo=UTC),
            duration_ms=200.0,
            token_usage=TokenUsage(input_tokens=100, output_tokens=0),
            cost_usd=0.0003,
            error_type="ValueError",
            error_message="Invalid ticket format",
        ),
    ]
