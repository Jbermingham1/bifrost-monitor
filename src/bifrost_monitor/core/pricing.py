"""Model pricing for token cost calculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bifrost_monitor.models.run import TokenUsage


@dataclass(frozen=True)
class ModelPrice:
    """Price per million tokens for a model."""

    input_per_m: float
    output_per_m: float
    cache_read_per_m: float = 0.0
    cache_creation_per_m: float = 0.0


# Prices per million tokens (USD) — verified against provider pricing pages 2026-07.
# Anthropic cache pricing: reads = 0.1x input, writes (5-min TTL) = 1.25x input.
_BUILTIN_PRICES: dict[str, ModelPrice] = {
    # Anthropic Claude
    "claude-fable-5": ModelPrice(10.0, 50.0, 1.0, 12.5),
    "claude-opus-4-8": ModelPrice(5.0, 25.0, 0.5, 6.25),
    "claude-opus-4-7": ModelPrice(5.0, 25.0, 0.5, 6.25),
    "claude-opus-4-6": ModelPrice(5.0, 25.0, 0.5, 6.25),
    "claude-sonnet-5": ModelPrice(3.0, 15.0, 0.3, 3.75),
    "claude-sonnet-4-6": ModelPrice(3.0, 15.0, 0.3, 3.75),
    "claude-haiku-4-5": ModelPrice(1.0, 5.0, 0.1, 1.25),
    # OpenAI GPT-4o / GPT-4.1
    "gpt-4o": ModelPrice(2.5, 10.0),
    "gpt-4o-mini": ModelPrice(0.15, 0.6),
    "gpt-4.1": ModelPrice(2.0, 8.0),
    "gpt-4.1-mini": ModelPrice(0.4, 1.6),
    "gpt-4.1-nano": ModelPrice(0.1, 0.4),
    # Google Gemini 2.5 (standard tier, prompts <= 200k tokens)
    "gemini-2.5-pro": ModelPrice(1.25, 10.0),
    "gemini-2.5-flash": ModelPrice(0.3, 2.5),
}


class ModelPricing:
    """Calculate costs from token usage and model name."""

    def __init__(self) -> None:
        self._prices: dict[str, ModelPrice] = dict(_BUILTIN_PRICES)

    def add_model(
        self,
        model: str,
        input_per_m: float,
        output_per_m: float,
        cache_read_per_m: float = 0.0,
        cache_creation_per_m: float = 0.0,
    ) -> None:
        """Register a custom model price."""
        self._prices[model] = ModelPrice(
            input_per_m, output_per_m, cache_read_per_m, cache_creation_per_m
        )

    def get_price(self, model: str) -> ModelPrice | None:
        """Get pricing for a model, or None if unknown."""
        return self._prices.get(model)

    def calculate_cost(self, model: str, usage: TokenUsage) -> float:
        """Calculate cost in USD. Returns 0.0 if model is unknown."""
        price = self._prices.get(model)
        if price is None:
            return 0.0
        cost = (
            (usage.input_tokens * price.input_per_m / 1_000_000)
            + (usage.output_tokens * price.output_per_m / 1_000_000)
            + (usage.cache_read_tokens * price.cache_read_per_m / 1_000_000)
            + (usage.cache_creation_tokens * price.cache_creation_per_m / 1_000_000)
        )
        return round(cost, 8)

    @property
    def supported_models(self) -> list[str]:
        """List all models with pricing."""
        return sorted(self._prices.keys())
