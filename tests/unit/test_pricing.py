"""Tests for pricing module."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bifrost_monitor.core.pricing import ModelPricing
from bifrost_monitor.models.run import TokenUsage


class TestModelPricing:
    def test_builtin_models_exist(self) -> None:
        p = ModelPricing()
        assert p.get_price("claude-sonnet-4-6") is not None
        assert p.get_price("gpt-4o") is not None
        assert p.get_price("gemini-2.5-pro") is not None

    def test_unknown_model_returns_none(self) -> None:
        p = ModelPricing()
        assert p.get_price("unknown-model") is None

    def test_unknown_model_cost_is_zero(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        assert p.calculate_cost("unknown-model", usage) == 0.0

    def test_zero_tokens_zero_cost(self) -> None:
        p = ModelPricing()
        assert p.calculate_cost("claude-sonnet-4-6", TokenUsage()) == 0.0

    def test_sonnet_cost_calculation(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = p.calculate_cost("claude-sonnet-4-6", usage)
        # $3/M input + $15/M output = $18
        assert cost == 18.0

    def test_opus_cost_calculation(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = p.calculate_cost("claude-opus-4-6", usage)
        # $5/M input + $25/M output = $30
        assert cost == 30.0

    def test_gpt4o_cost_calculation(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = p.calculate_cost("gpt-4o", usage)
        # $2.5/M input + $10/M output = $12.5
        assert cost == 12.5

    def test_cache_tokens_included(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=1_000_000,
            cache_creation_tokens=1_000_000,
        )
        cost = p.calculate_cost("claude-sonnet-4-6", usage)
        # $0.3/M cache_read + $3.75/M cache_creation = $4.05
        assert cost == 4.05

    def test_small_usage_precision(self) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        cost = p.calculate_cost("claude-sonnet-4-6", usage)
        # 100 * 3/1M + 50 * 15/1M = 0.0003 + 0.00075 = 0.00105
        assert cost == 0.00105

    def test_custom_model(self) -> None:
        p = ModelPricing()
        p.add_model("my-model", input_per_m=1.0, output_per_m=2.0)
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        assert p.calculate_cost("my-model", usage) == 3.0

    def test_supported_models_list(self) -> None:
        p = ModelPricing()
        models = p.supported_models
        assert isinstance(models, list)
        assert "claude-sonnet-4-6" in models
        assert models == sorted(models)

    def test_custom_model_with_cache_pricing(self) -> None:
        p = ModelPricing()
        p.add_model("cached-model", 1.0, 2.0, cache_read_per_m=0.5, cache_creation_per_m=1.0)
        usage = TokenUsage(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_read_tokens=1_000_000,
            cache_creation_tokens=1_000_000,
        )
        # 1 + 2 + 0.5 + 1 = 4.5
        assert p.calculate_cost("cached-model", usage) == 4.5


class TestPricingProperties:
    @given(
        input_tokens=st.integers(min_value=0, max_value=10_000_000),
        output_tokens=st.integers(min_value=0, max_value=10_000_000),
    )
    @settings(max_examples=50)
    def test_cost_is_non_negative(self, input_tokens: int, output_tokens: int) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        cost = p.calculate_cost("claude-sonnet-4-6", usage)
        assert cost >= 0.0

    @given(
        input_tokens=st.integers(min_value=0, max_value=10_000_000),
        output_tokens=st.integers(min_value=0, max_value=10_000_000),
    )
    @settings(max_examples=50)
    def test_more_tokens_more_cost(self, input_tokens: int, output_tokens: int) -> None:
        p = ModelPricing()
        usage_small = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        usage_big = TokenUsage(input_tokens=input_tokens + 1000, output_tokens=output_tokens + 1000)
        assert p.calculate_cost("claude-sonnet-4-6", usage_big) >= p.calculate_cost(
            "claude-sonnet-4-6", usage_small
        )

    @given(
        input_tokens=st.integers(min_value=1, max_value=10_000_000),
        output_tokens=st.integers(min_value=1, max_value=10_000_000),
    )
    @settings(max_examples=50)
    def test_opus_costs_more_than_sonnet(self, input_tokens: int, output_tokens: int) -> None:
        p = ModelPricing()
        usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        opus_cost = p.calculate_cost("claude-opus-4-6", usage)
        sonnet_cost = p.calculate_cost("claude-sonnet-4-6", usage)
        assert opus_cost >= sonnet_cost
