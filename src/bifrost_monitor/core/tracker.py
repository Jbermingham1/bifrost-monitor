"""MonitorTracker — the core decorator and run lifecycle manager."""

from __future__ import annotations

import functools
import inspect
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from bifrost_monitor.core.pricing import ModelPricing
from bifrost_monitor.models.run import RunRecord, RunStatus, TokenUsage


@runtime_checkable
class RunStore(Protocol):
    """Protocol for run storage backends."""

    def save(self, record: RunRecord) -> None: ...
    def query(self, **kwargs: Any) -> list[RunRecord]: ...


class InMemoryStore:
    """Simple in-memory store for testing."""

    def __init__(self) -> None:
        self.records: list[RunRecord] = []

    def save(self, record: RunRecord) -> None:
        self.records.append(record)

    def query(self, **kwargs: Any) -> list[RunRecord]:
        return list(self.records)


def _extract_token_usage(result: Any) -> TokenUsage | None:
    """Try to extract token usage from Anthropic/OpenAI response objects."""
    # Anthropic: result.usage.input_tokens / output_tokens
    usage_obj = getattr(result, "usage", None)
    if usage_obj is not None:
        input_tokens = getattr(usage_obj, "input_tokens", 0)
        output_tokens = getattr(usage_obj, "output_tokens", 0)
        cache_read = getattr(usage_obj, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(usage_obj, "cache_creation_input_tokens", 0) or 0
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
        )
    return None


class MonitorTracker:
    """Central tracker that records runs and calculates costs."""

    def __init__(
        self,
        store: RunStore | None = None,
        pricing: ModelPricing | None = None,
    ) -> None:
        self.store: RunStore = store or InMemoryStore()
        self.pricing = pricing or ModelPricing()

    def record(
        self,
        name: str,
        model: str = "",
        status: RunStatus = RunStatus.SUCCESS,
        duration_ms: float = 0.0,
        token_usage: TokenUsage | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunRecord:
        """Manually record a run."""
        usage = token_usage or TokenUsage()
        cost = self.pricing.calculate_cost(model, usage) if model else 0.0

        record = RunRecord(
            id=str(uuid.uuid4()),
            name=name,
            model=model,
            status=status,
            started_at=datetime.now(UTC),
            duration_ms=duration_ms,
            token_usage=usage,
            cost_usd=cost,
            error_type=error_type,
            error_message=error_message,
            metadata=metadata or {},
        )
        self.store.save(record)
        return record

    def monitor(
        self,
        name: str | None = None,
        model: str = "",
        auto_extract: bool = True,
    ) -> Any:
        """Decorator to monitor function execution.

        Supports both sync and async functions.
        Auto-extracts token usage from Anthropic/OpenAI response objects.
        """

        def decorator(func: Any) -> Any:
            func_name = name or func.__name__

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start) * 1000
                    usage = _extract_token_usage(result) if auto_extract else None
                    self.record(
                        name=func_name,
                        model=model,
                        status=RunStatus.SUCCESS,
                        duration_ms=duration_ms,
                        token_usage=usage,
                    )
                    return result
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start) * 1000
                    self.record(
                        name=func_name,
                        model=model,
                        status=RunStatus.ERROR,
                        duration_ms=duration_ms,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start) * 1000
                    usage = _extract_token_usage(result) if auto_extract else None
                    self.record(
                        name=func_name,
                        model=model,
                        status=RunStatus.SUCCESS,
                        duration_ms=duration_ms,
                        token_usage=usage,
                    )
                    return result
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start) * 1000
                    self.record(
                        name=func_name,
                        model=model,
                        status=RunStatus.ERROR,
                        duration_ms=duration_ms,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                    raise

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator
