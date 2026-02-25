"""Integration tests — full pipeline from decorator to CLI output."""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING

from bifrost_monitor.adapters.exporters import CSVExporter, JSONExporter
from bifrost_monitor.cli import main as cli_main
from bifrost_monitor.core.analyzer import RunAnalyzer
from bifrost_monitor.core.tracker import MonitorTracker
from bifrost_monitor.models.run import RunFilter, RunRecord, RunStatus, TokenUsage

if TYPE_CHECKING:
    from pathlib import Path

    from bifrost_monitor.adapters.sqlite import SQLiteStore


class TestSQLiteStore:
    def test_save_and_query(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="agent-a", model="claude-sonnet-4-6")
        tracker.record(name="agent-b", model="gpt-4o")
        records = store.query()
        assert len(records) == 2

    def test_filter_by_name(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="agent-a")
        tracker.record(name="agent-b")
        records = store.query(name="agent-a")
        assert len(records) == 1
        assert records[0].name == "agent-a"

    def test_filter_by_model(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a", model="claude-sonnet-4-6")
        tracker.record(name="b", model="gpt-4o")
        records = store.query(model="gpt-4o")
        assert len(records) == 1
        assert records[0].model == "gpt-4o"

    def test_filter_by_status(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a", status=RunStatus.SUCCESS)
        tracker.record(name="b", status=RunStatus.ERROR, error_type="Err", error_message="x")
        records = store.query(status=RunStatus.ERROR)
        assert len(records) == 1
        assert records[0].status == RunStatus.ERROR

    def test_count(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a")
        tracker.record(name="b")
        assert store.count() == 2

    def test_delete_all(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a")
        assert store.count() == 1
        store.delete_all()
        assert store.count() == 0

    def test_metadata_roundtrip(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a", metadata={"env": "prod", "version": 2})
        records = store.query()
        assert records[0].metadata["env"] == "prod"
        assert records[0].metadata["version"] == 2

    def test_token_usage_roundtrip(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        usage = TokenUsage(
            input_tokens=500,
            output_tokens=200,
            cache_read_tokens=50,
            cache_creation_tokens=25,
        )
        tracker.record(name="a", model="claude-sonnet-4-6", token_usage=usage)
        records = store.query()
        assert records[0].token_usage.input_tokens == 500
        assert records[0].token_usage.cache_read_tokens == 50

    def test_limit(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        for i in range(10):
            tracker.record(name=f"agent-{i}")
        records = store.query(limit=3)
        assert len(records) == 3

    def test_query_filter_object(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)
        tracker.record(name="a", model="gpt-4o")
        tracker.record(name="b", model="claude-sonnet-4-6")
        f = RunFilter(model="gpt-4o")
        records = store.query_filter(f)
        assert len(records) == 1


class TestFullPipeline:
    def test_decorator_to_analysis(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="pipeline-test", model="claude-sonnet-4-6")
        def do_work(x: int) -> int:
            return x + 1

        for _ in range(5):
            do_work(1)

        records = store.query()
        assert len(records) == 5

        analyzer = RunAnalyzer(records)
        summary = analyzer.summary()
        assert summary.total_runs == 5
        assert summary.success_rate == 100.0

        cost_report = analyzer.cost_report()
        assert cost_report.total_runs == 5

    def test_error_flow(self, store: SQLiteStore) -> None:
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="error-test")
        def failing(x: int) -> int:
            if x < 0:
                raise ValueError("negative")
            return x

        failing(1)
        with contextlib.suppress(ValueError):
            failing(-1)

        records = store.query()
        assert len(records) == 2

        errors = RunAnalyzer(records).error_summary()
        assert errors.total_errors == 1
        assert errors.error_groups[0].error_type == "ValueError"

    def test_sample_records_analysis(
        self, store: SQLiteStore, sample_records: list[RunRecord]
    ) -> None:
        for r in sample_records:
            store.save(r)

        records = store.query()
        assert len(records) == 3

        summary = RunAnalyzer(records).summary()
        assert summary.total_runs == 3
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1


class TestExporters:
    def test_json_export(self, sample_records: list[RunRecord]) -> None:
        output = JSONExporter.export(sample_records)
        data = json.loads(output)
        assert len(data) == 3
        assert data[0]["name"] == "support-agent"

    def test_csv_export(self, sample_records: list[RunRecord]) -> None:
        output = CSVExporter.export(sample_records)
        lines = output.strip().split("\n")
        assert len(lines) == 4  # header + 3 records
        assert "support-agent" in lines[1]

    def test_empty_export(self) -> None:
        assert JSONExporter.export([]) == "[]"
        csv_out = CSVExporter.export([])
        lines = csv_out.strip().split("\n")
        assert len(lines) == 1  # header only


class TestCLI:
    def _seed(
        self,
        store: SQLiteStore,
        records: list[RunRecord],
    ) -> None:
        for r in records:
            store.save(r)
        store.close()

    def test_runs_command(
        self,
        store: SQLiteStore,
        sample_records: list[RunRecord],
        tmp_db: Path,
    ) -> None:
        self._seed(store, sample_records)
        cli_main(["--db", str(tmp_db), "runs"])

    def test_costs_command(
        self,
        store: SQLiteStore,
        sample_records: list[RunRecord],
        tmp_db: Path,
    ) -> None:
        self._seed(store, sample_records)
        cli_main(["--db", str(tmp_db), "costs", "--group-by", "model"])

    def test_errors_command(
        self,
        store: SQLiteStore,
        sample_records: list[RunRecord],
        tmp_db: Path,
    ) -> None:
        self._seed(store, sample_records)
        cli_main(["--db", str(tmp_db), "errors"])

    def test_summary_command(
        self,
        store: SQLiteStore,
        sample_records: list[RunRecord],
        tmp_db: Path,
    ) -> None:
        self._seed(store, sample_records)
        cli_main(["--db", str(tmp_db), "summary"])

    def test_empty_db(self, tmp_db: Path) -> None:
        cli_main(["--db", str(tmp_db), "runs"])

    def test_costs_by_name(
        self,
        store: SQLiteStore,
        sample_records: list[RunRecord],
        tmp_db: Path,
    ) -> None:
        self._seed(store, sample_records)
        cli_main(["--db", str(tmp_db), "costs", "--group-by", "name"])
