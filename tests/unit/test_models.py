"""Tests for bifrost-monitor data models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bifrost_monitor.models.report import CostReport, ErrorGroup, ErrorSummary, RunSummary
from bifrost_monitor.models.run import RunFilter, RunRecord, RunStatus, TokenUsage


class TestTokenUsage:
    def test_default_values(self) -> None:
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.cache_creation_tokens == 0

    def test_total_tokens(self) -> None:
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_total_tokens_ignores_cache(self) -> None:
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=30,
            cache_creation_tokens=20,
        )
        assert usage.total_tokens == 150


class TestRunStatus:
    def test_enum_values(self) -> None:
        assert RunStatus.SUCCESS == "success"
        assert RunStatus.ERROR == "error"
        assert RunStatus.TIMEOUT == "timeout"

    def test_string_comparison(self) -> None:
        assert RunStatus.SUCCESS == "success"
        assert RunStatus("error") == RunStatus.ERROR


class TestRunRecord:
    def test_minimal_creation(self) -> None:
        record = RunRecord(name="test-agent")
        assert record.name == "test-agent"
        assert record.status == RunStatus.SUCCESS
        assert record.model == ""
        assert record.cost_usd == 0.0

    def test_full_creation(self) -> None:
        record = RunRecord(
            id="run-123",
            name="support-agent",
            model="claude-sonnet-4-6",
            status=RunStatus.SUCCESS,
            duration_ms=1500.0,
            token_usage=TokenUsage(input_tokens=200, output_tokens=100),
            cost_usd=0.003,
        )
        assert record.id == "run-123"
        assert record.model == "claude-sonnet-4-6"
        assert record.duration_ms == 1500.0
        assert record.token_usage.total_tokens == 300
        assert record.cost_usd == 0.003

    def test_error_record(self) -> None:
        record = RunRecord(
            name="failing-agent",
            status=RunStatus.ERROR,
            error_type="ValueError",
            error_message="Invalid input",
        )
        assert record.status == RunStatus.ERROR
        assert record.error_type == "ValueError"
        assert record.error_message == "Invalid input"

    def test_duration_property(self) -> None:
        record = RunRecord(name="test", duration_ms=2500.0)
        assert record.duration == timedelta(milliseconds=2500)

    def test_metadata_field(self) -> None:
        record = RunRecord(name="test", metadata={"env": "prod", "version": "1.0"})
        assert record.metadata["env"] == "prod"


class TestRunFilter:
    def test_default_filter(self) -> None:
        f = RunFilter()
        assert f.name is None
        assert f.model is None
        assert f.limit == 100

    def test_last_hours_filter(self) -> None:
        f = RunFilter(last_hours=24)
        since = f.get_since()
        assert since is not None
        assert (datetime.now(UTC) - since).total_seconds() == pytest.approx(24 * 3600, abs=5)

    def test_last_days_filter(self) -> None:
        f = RunFilter(last_days=7)
        since = f.get_since()
        assert since is not None
        assert (datetime.now(UTC) - since).total_seconds() == pytest.approx(7 * 24 * 3600, abs=5)

    def test_explicit_since(self) -> None:
        dt = datetime(2025, 1, 1)
        f = RunFilter(since=dt)
        assert f.get_since() == dt

    def test_since_takes_priority(self) -> None:
        dt = datetime(2025, 6, 1)
        f = RunFilter(since=dt, last_hours=24)
        assert f.get_since() == dt

    def test_no_time_filter(self) -> None:
        f = RunFilter(name="test")
        assert f.get_since() is None

    def test_status_filter(self) -> None:
        f = RunFilter(status=RunStatus.ERROR)
        assert f.status == RunStatus.ERROR


class TestCostReport:
    def test_empty_report(self) -> None:
        report = CostReport()
        assert report.total_cost_usd == 0.0
        assert report.total_runs == 0
        assert report.cost_by_model == {}

    def test_populated_report(self) -> None:
        report = CostReport(
            total_cost_usd=1.50,
            total_runs=100,
            cost_by_model={"claude-sonnet-4-6": 1.0, "gpt-4o": 0.5},
            avg_cost_per_run=0.015,
        )
        assert report.total_cost_usd == 1.50
        assert len(report.cost_by_model) == 2


class TestRunSummary:
    def test_empty_summary(self) -> None:
        summary = RunSummary()
        assert summary.success_rate == 0.0

    def test_success_rate(self) -> None:
        summary = RunSummary(total_runs=100, successful_runs=95, failed_runs=5)
        assert summary.success_rate == 95.0

    def test_full_summary(self) -> None:
        summary = RunSummary(
            total_runs=200,
            successful_runs=180,
            failed_runs=15,
            timeout_runs=5,
            avg_duration_ms=1200.0,
            total_tokens=50000,
            total_cost_usd=2.50,
            runs_by_name={"agent-a": 100, "agent-b": 100},
            runs_by_model={"claude-sonnet-4-6": 150, "gpt-4o": 50},
        )
        assert summary.success_rate == 90.0
        assert len(summary.runs_by_name) == 2


class TestErrorSummary:
    def test_empty_errors(self) -> None:
        errors = ErrorSummary()
        assert errors.total_errors == 0
        assert errors.error_groups == []

    def test_error_groups(self) -> None:
        group = ErrorGroup(
            error_type="ValueError",
            count=5,
            latest_message="Bad input",
            affected_names=["agent-a", "agent-b"],
        )
        errors = ErrorSummary(total_errors=5, error_groups=[group])
        assert errors.total_errors == 5
        assert errors.error_groups[0].error_type == "ValueError"
        assert len(errors.error_groups[0].affected_names) == 2
