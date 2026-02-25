"""Run data models for bifrost-monitor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Status of a monitored run."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class TokenUsage(BaseModel):
    """Token usage for a single run."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed."""
        return self.input_tokens + self.output_tokens


class RunRecord(BaseModel):
    """A single monitored run record."""

    id: str = Field(default_factory=lambda: "")
    name: str
    model: str = ""
    status: RunStatus = RunStatus.SUCCESS
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float = 0.0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration(self) -> timedelta:
        """Duration as timedelta."""
        return timedelta(milliseconds=self.duration_ms)


class RunFilter(BaseModel):
    """Filter criteria for querying runs."""

    name: str | None = None
    model: str | None = None
    status: RunStatus | None = None
    last_hours: float | None = None
    last_days: float | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = 100

    def get_since(self) -> datetime | None:
        """Resolve the effective 'since' timestamp."""
        if self.since is not None:
            return self.since
        if self.last_hours is not None:
            return datetime.now(UTC) - timedelta(hours=self.last_hours)
        if self.last_days is not None:
            return datetime.now(UTC) - timedelta(days=self.last_days)
        return None
