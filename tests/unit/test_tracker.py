"""Tests for tracker module."""

from __future__ import annotations

import asyncio

import pytest

from bifrost_monitor.core.tracker import InMemoryStore, MonitorTracker, _extract_token_usage
from bifrost_monitor.models.run import RunStatus, TokenUsage


class TestInMemoryStore:
    def test_save_and_query(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)
        tracker.record(name="test", model="gpt-4o")
        assert len(store.records) == 1

    def test_query_returns_all(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)
        tracker.record(name="a")
        tracker.record(name="b")
        assert len(store.query()) == 2


class TestMonitorTracker:
    def test_record_basic(self) -> None:
        tracker = MonitorTracker()
        record = tracker.record(name="my-agent", model="claude-sonnet-4-6")
        assert record.name == "my-agent"
        assert record.model == "claude-sonnet-4-6"
        assert record.status == RunStatus.SUCCESS
        assert record.id != ""

    def test_record_with_tokens(self) -> None:
        tracker = MonitorTracker()
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        record = tracker.record(name="agent", model="claude-sonnet-4-6", token_usage=usage)
        assert record.token_usage.total_tokens == 1500
        assert record.cost_usd > 0

    def test_record_error(self) -> None:
        tracker = MonitorTracker()
        record = tracker.record(
            name="agent",
            status=RunStatus.ERROR,
            error_type="ValueError",
            error_message="bad input",
        )
        assert record.status == RunStatus.ERROR
        assert record.error_type == "ValueError"

    def test_record_no_model_zero_cost(self) -> None:
        tracker = MonitorTracker()
        record = tracker.record(name="agent")
        assert record.cost_usd == 0.0

    def test_record_stored(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)
        tracker.record(name="a")
        tracker.record(name="b")
        assert len(store.records) == 2

    def test_record_with_metadata(self) -> None:
        tracker = MonitorTracker()
        record = tracker.record(name="agent", metadata={"env": "prod"})
        assert record.metadata["env"] == "prod"


class TestMonitorDecorator:
    def test_sync_function(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="sync-test")
        def my_func(x: int) -> int:
            return x * 2

        result = my_func(5)
        assert result == 10
        assert len(store.records) == 1
        assert store.records[0].name == "sync-test"
        assert store.records[0].status == RunStatus.SUCCESS
        assert store.records[0].duration_ms > 0

    def test_async_function(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="async-test")
        async def my_async_func(x: int) -> int:
            return x * 3

        result = asyncio.run(my_async_func(4))
        assert result == 12
        assert len(store.records) == 1
        assert store.records[0].name == "async-test"
        assert store.records[0].status == RunStatus.SUCCESS

    def test_sync_error_captured(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="error-test")
        def failing_func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            failing_func()

        assert len(store.records) == 1
        assert store.records[0].status == RunStatus.ERROR
        assert store.records[0].error_type == "ValueError"
        assert store.records[0].error_message == "boom"

    def test_async_error_captured(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="async-error")
        async def failing_async() -> None:
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError, match="async boom"):
            asyncio.run(failing_async())

        assert len(store.records) == 1
        assert store.records[0].status == RunStatus.ERROR
        assert store.records[0].error_type == "RuntimeError"

    def test_default_name_from_function(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor()
        def my_cool_function() -> str:
            return "ok"

        my_cool_function()
        assert store.records[0].name == "my_cool_function"

    def test_model_passed_to_record(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        @tracker.monitor(name="test", model="claude-sonnet-4-6")
        def func() -> str:
            return "ok"

        func()
        assert store.records[0].model == "claude-sonnet-4-6"

    def test_auto_extract_anthropic_response(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        class MockUsage:
            input_tokens = 500
            output_tokens = 200
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0

        class MockResponse:
            usage = MockUsage()
            content = "hello"

        @tracker.monitor(name="extract-test", model="claude-sonnet-4-6")
        def func() -> MockResponse:
            return MockResponse()

        func()
        record = store.records[0]
        assert record.token_usage.input_tokens == 500
        assert record.token_usage.output_tokens == 200
        assert record.cost_usd > 0

    def test_auto_extract_disabled(self) -> None:
        store = InMemoryStore()
        tracker = MonitorTracker(store=store)

        class MockUsage:
            input_tokens = 500
            output_tokens = 200
            cache_read_input_tokens = None
            cache_creation_input_tokens = None

        class MockResponse:
            usage = MockUsage()

        @tracker.monitor(name="no-extract", auto_extract=False)
        def func() -> MockResponse:
            return MockResponse()

        func()
        assert store.records[0].token_usage.input_tokens == 0


class TestExtractTokenUsage:
    def test_no_usage_attr(self) -> None:
        assert _extract_token_usage("plain string") is None

    def test_anthropic_style(self) -> None:
        class Usage:
            input_tokens = 100
            output_tokens = 50
            cache_read_input_tokens = 10
            cache_creation_input_tokens = 5

        class Response:
            usage = Usage()

        result = _extract_token_usage(Response())
        assert result is not None
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.cache_read_tokens == 10
        assert result.cache_creation_tokens == 5

    def test_openai_style(self) -> None:
        class Usage:
            input_tokens = 200  # noqa: N815
            output_tokens = 100  # noqa: N815

        class Response:
            usage = Usage()

        result = _extract_token_usage(Response())
        assert result is not None
        assert result.input_tokens == 200
        assert result.output_tokens == 100
