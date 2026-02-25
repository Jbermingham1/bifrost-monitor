"""Tests for analyzer module."""

from __future__ import annotations

from datetime import UTC, datetime

from bifrost_monitor.core.analyzer import RunAnalyzer
from bifrost_monitor.models.run import RunRecord, RunStatus, TokenUsage


def _make_record(
    name: str = "agent",
    model: str = "claude-sonnet-4-6",
    status: RunStatus = RunStatus.SUCCESS,
    duration_ms: float = 1000.0,
    input_tokens: int = 100,
    output_tokens: int = 50,
    cost_usd: float = 0.001,
    error_type: str | None = None,
    error_message: str | None = None,
) -> RunRecord:
    return RunRecord(
        id="test-id",
        name=name,
        model=model,
        status=status,
        started_at=datetime.now(UTC),
        duration_ms=duration_ms,
        token_usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        cost_usd=cost_usd,
        error_type=error_type,
        error_message=error_message,
    )


class TestRunAnalyzerSummary:
    def test_empty_records(self) -> None:
        analyzer = RunAnalyzer([])
        summary = analyzer.summary()
        assert summary.total_runs == 0
        assert summary.success_rate == 0.0

    def test_single_successful_run(self) -> None:
        records = [_make_record()]
        summary = RunAnalyzer(records).summary()
        assert summary.total_runs == 1
        assert summary.successful_runs == 1
        assert summary.failed_runs == 0
        assert summary.success_rate == 100.0

    def test_mixed_statuses(self) -> None:
        records = [
            _make_record(status=RunStatus.SUCCESS),
            _make_record(status=RunStatus.SUCCESS),
            _make_record(status=RunStatus.ERROR),
            _make_record(status=RunStatus.TIMEOUT),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.total_runs == 4
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1
        assert summary.timeout_runs == 1
        assert summary.success_rate == 50.0

    def test_avg_duration(self) -> None:
        records = [
            _make_record(duration_ms=1000),
            _make_record(duration_ms=3000),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.avg_duration_ms == 2000.0

    def test_total_tokens(self) -> None:
        records = [
            _make_record(input_tokens=100, output_tokens=50),
            _make_record(input_tokens=200, output_tokens=100),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.total_tokens == 450

    def test_total_cost(self) -> None:
        records = [
            _make_record(cost_usd=0.01),
            _make_record(cost_usd=0.02),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.total_cost_usd == 0.03

    def test_runs_by_name(self) -> None:
        records = [
            _make_record(name="agent-a"),
            _make_record(name="agent-a"),
            _make_record(name="agent-b"),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.runs_by_name["agent-a"] == 2
        assert summary.runs_by_name["agent-b"] == 1

    def test_runs_by_model(self) -> None:
        records = [
            _make_record(model="claude-sonnet-4-6"),
            _make_record(model="gpt-4o"),
            _make_record(model="gpt-4o"),
        ]
        summary = RunAnalyzer(records).summary()
        assert summary.runs_by_model["claude-sonnet-4-6"] == 1
        assert summary.runs_by_model["gpt-4o"] == 2

    def test_empty_model_excluded_from_runs_by_model(self) -> None:
        records = [_make_record(model="")]
        summary = RunAnalyzer(records).summary()
        assert summary.runs_by_model == {}


class TestRunAnalyzerCostReport:
    def test_empty_records(self) -> None:
        report = RunAnalyzer([]).cost_report()
        assert report.total_cost_usd == 0.0
        assert report.total_runs == 0

    def test_cost_by_model(self) -> None:
        records = [
            _make_record(model="claude-sonnet-4-6", cost_usd=0.01),
            _make_record(model="gpt-4o", cost_usd=0.02),
            _make_record(model="claude-sonnet-4-6", cost_usd=0.03),
        ]
        report = RunAnalyzer(records).cost_report()
        assert report.cost_by_model["claude-sonnet-4-6"] == 0.04
        assert report.cost_by_model["gpt-4o"] == 0.02
        assert report.total_cost_usd == 0.06

    def test_cost_by_name(self) -> None:
        records = [
            _make_record(name="support", cost_usd=0.05),
            _make_record(name="triage", cost_usd=0.03),
        ]
        report = RunAnalyzer(records).cost_report()
        assert report.cost_by_name["support"] == 0.05
        assert report.cost_by_name["triage"] == 0.03

    def test_avg_cost_per_run(self) -> None:
        records = [
            _make_record(cost_usd=0.10),
            _make_record(cost_usd=0.20),
        ]
        report = RunAnalyzer(records).cost_report()
        assert report.avg_cost_per_run == 0.15


class TestRunAnalyzerErrorSummary:
    def test_no_errors(self) -> None:
        records = [_make_record()]
        errors = RunAnalyzer(records).error_summary()
        assert errors.total_errors == 0
        assert errors.error_groups == []

    def test_single_error_type(self) -> None:
        records = [
            _make_record(
                status=RunStatus.ERROR,
                error_type="ValueError",
                error_message="bad input",
            ),
        ]
        errors = RunAnalyzer(records).error_summary()
        assert errors.total_errors == 1
        assert len(errors.error_groups) == 1
        assert errors.error_groups[0].error_type == "ValueError"
        assert errors.error_groups[0].count == 1

    def test_multiple_error_types_sorted_by_count(self) -> None:
        records = [
            _make_record(status=RunStatus.ERROR, error_type="ValueError", error_message="a"),
            _make_record(status=RunStatus.ERROR, error_type="ValueError", error_message="b"),
            _make_record(status=RunStatus.ERROR, error_type="TypeError", error_message="c"),
        ]
        errors = RunAnalyzer(records).error_summary()
        assert errors.total_errors == 3
        assert errors.error_groups[0].error_type == "ValueError"
        assert errors.error_groups[0].count == 2
        assert errors.error_groups[1].error_type == "TypeError"
        assert errors.error_groups[1].count == 1

    def test_affected_names_tracked(self) -> None:
        records = [
            _make_record(name="agent-a", status=RunStatus.ERROR, error_type="ValueError"),
            _make_record(name="agent-b", status=RunStatus.ERROR, error_type="ValueError"),
            _make_record(name="agent-a", status=RunStatus.ERROR, error_type="ValueError"),
        ]
        errors = RunAnalyzer(records).error_summary()
        group = errors.error_groups[0]
        assert set(group.affected_names) == {"agent-a", "agent-b"}

    def test_unknown_error_type(self) -> None:
        records = [
            _make_record(status=RunStatus.ERROR, error_type=None, error_message="mystery"),
        ]
        errors = RunAnalyzer(records).error_summary()
        assert errors.error_groups[0].error_type == "Unknown"

    def test_latest_message_updated(self) -> None:
        records = [
            _make_record(status=RunStatus.ERROR, error_type="Err", error_message="first"),
            _make_record(status=RunStatus.ERROR, error_type="Err", error_message="second"),
        ]
        errors = RunAnalyzer(records).error_summary()
        assert errors.error_groups[0].latest_message == "second"
