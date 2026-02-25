"""Report data models for bifrost-monitor."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CostReport(BaseModel):
    """Aggregated cost report."""

    total_cost_usd: float = 0.0
    total_runs: int = 0
    cost_by_model: dict[str, float] = Field(default_factory=dict)
    cost_by_name: dict[str, float] = Field(default_factory=dict)
    avg_cost_per_run: float = 0.0


class RunSummary(BaseModel):
    """Summary statistics for runs."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    timeout_runs: int = 0
    avg_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    runs_by_name: dict[str, int] = Field(default_factory=dict)
    runs_by_model: dict[str, int] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100.0


class ErrorGroup(BaseModel):
    """A group of errors with the same type."""

    error_type: str
    count: int = 0
    latest_message: str = ""
    affected_names: list[str] = Field(default_factory=list)


class ErrorSummary(BaseModel):
    """Summary of errors across runs."""

    total_errors: int = 0
    error_groups: list[ErrorGroup] = Field(default_factory=lambda: list[ErrorGroup]())
