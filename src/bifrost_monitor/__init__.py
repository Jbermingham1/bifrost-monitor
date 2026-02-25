"""bifrost-monitor: Zero-config AI agent observability."""

from bifrost_monitor.core.pricing import ModelPricing
from bifrost_monitor.core.tracker import MonitorTracker
from bifrost_monitor.models.report import CostReport, ErrorSummary, RunSummary
from bifrost_monitor.models.run import RunFilter, RunRecord, RunStatus, TokenUsage

__version__ = "0.1.0"

__all__ = [
    "CostReport",
    "ErrorSummary",
    "ModelPricing",
    "MonitorTracker",
    "RunFilter",
    "RunRecord",
    "RunStatus",
    "RunSummary",
    "TokenUsage",
]

# Convenience: module-level tracker for quick usage
_default_tracker = MonitorTracker()
monitor = _default_tracker.monitor
record = _default_tracker.record
