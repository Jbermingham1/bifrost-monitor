"""RunAnalyzer — aggregate stats, cost reports, error grouping."""

from __future__ import annotations

from collections import defaultdict

from bifrost_monitor.models.report import CostReport, ErrorGroup, ErrorSummary, RunSummary
from bifrost_monitor.models.run import RunRecord, RunStatus


class RunAnalyzer:
    """Analyze a collection of run records."""

    def __init__(self, records: list[RunRecord]) -> None:
        self._records = records

    def summary(self) -> RunSummary:
        """Generate a run summary from records."""
        if not self._records:
            return RunSummary()

        successful = sum(1 for r in self._records if r.status == RunStatus.SUCCESS)
        failed = sum(1 for r in self._records if r.status == RunStatus.ERROR)
        timeouts = sum(1 for r in self._records if r.status == RunStatus.TIMEOUT)
        total_duration = sum(r.duration_ms for r in self._records)
        total_tokens = sum(r.token_usage.total_tokens for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)

        runs_by_name: dict[str, int] = defaultdict(int)
        runs_by_model: dict[str, int] = defaultdict(int)
        for r in self._records:
            runs_by_name[r.name] += 1
            if r.model:
                runs_by_model[r.model] += 1

        return RunSummary(
            total_runs=len(self._records),
            successful_runs=successful,
            failed_runs=failed,
            timeout_runs=timeouts,
            avg_duration_ms=total_duration / len(self._records),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            runs_by_name=dict(runs_by_name),
            runs_by_model=dict(runs_by_model),
        )

    def cost_report(self) -> CostReport:
        """Generate a cost report from records."""
        if not self._records:
            return CostReport()

        total_cost = sum(r.cost_usd for r in self._records)
        cost_by_model: dict[str, float] = defaultdict(float)
        cost_by_name: dict[str, float] = defaultdict(float)

        for r in self._records:
            if r.model:
                cost_by_model[r.model] += r.cost_usd
            cost_by_name[r.name] += r.cost_usd

        return CostReport(
            total_cost_usd=round(total_cost, 6),
            total_runs=len(self._records),
            cost_by_model={k: round(v, 6) for k, v in cost_by_model.items()},
            cost_by_name={k: round(v, 6) for k, v in cost_by_name.items()},
            avg_cost_per_run=round(total_cost / len(self._records), 8),
        )

    def error_summary(self) -> ErrorSummary:
        """Generate an error summary from records."""
        error_records = [r for r in self._records if r.status == RunStatus.ERROR]
        if not error_records:
            return ErrorSummary()

        groups: dict[str, ErrorGroup] = {}
        for r in error_records:
            error_type = r.error_type or "Unknown"
            if error_type not in groups:
                groups[error_type] = ErrorGroup(error_type=error_type)
            group = groups[error_type]
            group.count += 1
            group.latest_message = r.error_message or ""
            if r.name not in group.affected_names:
                group.affected_names.append(r.name)

        return ErrorSummary(
            total_errors=len(error_records),
            error_groups=sorted(groups.values(), key=lambda g: g.count, reverse=True),
        )
