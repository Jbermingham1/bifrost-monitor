"""Export adapters for run data."""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bifrost_monitor.models.run import RunRecord


class JSONExporter:
    """Export runs as JSON."""

    @staticmethod
    def export(records: list[RunRecord]) -> str:
        """Export records to JSON string."""
        data: list[dict[str, Any]] = []
        for r in records:
            data.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "model": r.model,
                    "status": r.status.value,
                    "started_at": r.started_at.isoformat(),
                    "duration_ms": r.duration_ms,
                    "input_tokens": r.token_usage.input_tokens,
                    "output_tokens": r.token_usage.output_tokens,
                    "cost_usd": r.cost_usd,
                    "error_type": r.error_type,
                    "error_message": r.error_message,
                }
            )
        return json.dumps(data, indent=2)


class CSVExporter:
    """Export runs as CSV."""

    _FIELDS = [
        "id",
        "name",
        "model",
        "status",
        "started_at",
        "duration_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "error_type",
        "error_message",
    ]

    @staticmethod
    def export(records: list[RunRecord]) -> str:
        """Export records to CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSVExporter._FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "id": r.id,
                    "name": r.name,
                    "model": r.model,
                    "status": r.status.value,
                    "started_at": r.started_at.isoformat(),
                    "duration_ms": r.duration_ms,
                    "input_tokens": r.token_usage.input_tokens,
                    "output_tokens": r.token_usage.output_tokens,
                    "cost_usd": r.cost_usd,
                    "error_type": r.error_type or "",
                    "error_message": r.error_message or "",
                }
            )
        return output.getvalue()
