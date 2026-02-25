"""CLI for bifrost-monitor — query runs, costs, errors, and summaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from bifrost_monitor.adapters.sqlite import SQLiteStore
from bifrost_monitor.core.analyzer import RunAnalyzer
from bifrost_monitor.models.run import RunFilter, RunStatus


def _parse_last(value: str) -> tuple[float | None, float | None]:
    """Parse --last value like '24h' or '7d'."""
    value = value.strip().lower()
    if value.endswith("h"):
        return float(value[:-1]), None
    if value.endswith("d"):
        return None, float(value[:-1])
    raise argparse.ArgumentTypeError(f"Invalid --last format: {value!r}. Use '24h' or '7d'.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bifrost-monitor",
        description="Zero-config AI agent observability",
    )
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database")

    sub = parser.add_subparsers(dest="command")

    # runs
    runs_p = sub.add_parser("runs", help="List recent runs")
    runs_p.add_argument("--last", type=str, default=None, help="Time window (e.g. 24h, 7d)")
    runs_p.add_argument("--name", type=str, default=None)
    runs_p.add_argument("--model", type=str, default=None)
    runs_p.add_argument("--status", type=str, default=None, choices=["success", "error", "timeout"])
    runs_p.add_argument("--limit", type=int, default=50)

    # costs
    costs_p = sub.add_parser("costs", help="Cost breakdown")
    costs_p.add_argument("--last", type=str, default=None)
    costs_p.add_argument("--name", type=str, default=None)
    costs_p.add_argument("--model", type=str, default=None)
    costs_p.add_argument("--group-by", type=str, choices=["model", "name"], default="model")

    # errors
    errors_p = sub.add_parser("errors", help="Error summary")
    errors_p.add_argument("--last", type=str, default=None)
    errors_p.add_argument("--name", type=str, default=None)

    # summary
    summary_p = sub.add_parser("summary", help="Run summary")
    summary_p.add_argument("--last", type=str, default=None)
    summary_p.add_argument("--name", type=str, default=None)
    summary_p.add_argument("--model", type=str, default=None)

    return parser


def _make_filter(args: argparse.Namespace) -> RunFilter:
    last_hours = None
    last_days = None
    last_val = getattr(args, "last", None)
    if last_val:
        last_hours, last_days = _parse_last(last_val)

    return RunFilter(
        name=getattr(args, "name", None),
        model=getattr(args, "model", None),
        status=RunStatus(args.status) if getattr(args, "status", None) else None,
        last_hours=last_hours,
        last_days=last_days,
        limit=getattr(args, "limit", 100),
    )


def _cmd_runs(store: SQLiteStore, args: argparse.Namespace) -> None:
    console = Console()
    run_filter = _make_filter(args)
    records = store.query_filter(run_filter)

    if not records:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title=f"Recent Runs ({len(records)})")
    table.add_column("Name", style="cyan")
    table.add_column("Model", style="magenta")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Time")

    for r in records:
        status_style = {
            RunStatus.SUCCESS: "[green]OK[/green]",
            RunStatus.ERROR: "[red]ERR[/red]",
            RunStatus.TIMEOUT: "[yellow]TMO[/yellow]",
        }.get(r.status, r.status.value)

        table.add_row(
            r.name,
            r.model or "-",
            status_style,
            f"{r.duration_ms:.0f}ms",
            str(r.token_usage.total_tokens),
            f"${r.cost_usd:.6f}",
            r.started_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def _cmd_costs(store: SQLiteStore, args: argparse.Namespace) -> None:
    console = Console()
    run_filter = _make_filter(args)
    records = store.query_filter(run_filter)
    report = RunAnalyzer(records).cost_report()

    if report.total_runs == 0:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title="Cost Breakdown")
    group_by: str = args.group_by

    if group_by == "model":
        table.add_column("Model", style="magenta")
        table.add_column("Cost", justify="right", style="green")
        for model, cost in sorted(report.cost_by_model.items(), key=lambda x: x[1], reverse=True):
            table.add_row(model, f"${cost:.6f}")
    else:
        table.add_column("Name", style="cyan")
        table.add_column("Cost", justify="right", style="green")
        for name, cost in sorted(report.cost_by_name.items(), key=lambda x: x[1], reverse=True):
            table.add_row(name, f"${cost:.6f}")

    console.print(table)
    total = report.total_cost_usd
    avg = report.avg_cost_per_run
    console.print(
        f"\n[bold]Total:[/bold] ${total:.6f} across {report.total_runs} runs (avg ${avg:.6f}/run)"
    )


def _cmd_errors(store: SQLiteStore, args: argparse.Namespace) -> None:
    console = Console()
    run_filter = _make_filter(args)
    run_filter.status = RunStatus.ERROR
    records = store.query_filter(run_filter)
    errors = RunAnalyzer(records).error_summary()

    if errors.total_errors == 0:
        console.print("[green]No errors found.[/green]")
        return

    table = Table(title=f"Errors ({errors.total_errors})")
    table.add_column("Type", style="red")
    table.add_column("Count", justify="right")
    table.add_column("Latest Message")
    table.add_column("Affected Agents")

    for g in errors.error_groups:
        table.add_row(
            g.error_type,
            str(g.count),
            g.latest_message[:60],
            ", ".join(g.affected_names),
        )

    console.print(table)


def _cmd_summary(store: SQLiteStore, args: argparse.Namespace) -> None:
    console = Console()
    run_filter = _make_filter(args)
    records = store.query_filter(run_filter)
    summary = RunAnalyzer(records).summary()

    if summary.total_runs == 0:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title="Run Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total Runs", str(summary.total_runs))
    table.add_row("Successful", f"[green]{summary.successful_runs}[/green]")
    table.add_row("Failed", f"[red]{summary.failed_runs}[/red]")
    table.add_row("Timeouts", f"[yellow]{summary.timeout_runs}[/yellow]")
    table.add_row("Success Rate", f"{summary.success_rate:.1f}%")
    table.add_row("Avg Duration", f"{summary.avg_duration_ms:.0f}ms")
    table.add_row("Total Tokens", f"{summary.total_tokens:,}")
    table.add_row("Total Cost", f"${summary.total_cost_usd:.6f}")

    console.print(table)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    db_path = Path(args.db) if args.db else None
    store = SQLiteStore(db_path=db_path)

    try:
        commands = {
            "runs": _cmd_runs,
            "costs": _cmd_costs,
            "errors": _cmd_errors,
            "summary": _cmd_summary,
        }
        cmd_func = commands.get(args.command)
        if cmd_func:
            cmd_func(store, args)
        else:
            parser.print_help()
            sys.exit(1)
    finally:
        store.close()


if __name__ == "__main__":
    main()
