# bifrost-monitor

[![CI](https://github.com/Jbermingham1/bifrost-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Jbermingham1/bifrost-monitor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Zero-config AI agent observability.** One decorator. Local SQLite. Instant insights.

No SaaS account. No API proxy. No infrastructure. One install command and one line of code.

## Why?

Hosted observability platforms (LangSmith, Helicone, Weights & Biases) are excellent
when you want a managed UI, team features, and cloud storage — at the cost of an
account, an API key or proxy in your request path, and your traces living in their
cloud. `bifrost-monitor` is the other end of the trade: a small local library, no
account, no proxy, and every trace stays in a SQLite file on your machine.

| | Hosted platforms | **bifrost-monitor** |
|------|------|------|
| Setup | Account + API key/proxy | one `pip install` |
| Your trace data | Their cloud | **Your machine** |
| UI & team features | Rich, managed | CLI only |

## Quick Start

```bash
pip install git+https://github.com/Jbermingham1/bifrost-monitor.git
```

```python
from bifrost_monitor import monitor

@monitor(name="support-agent", model="claude-sonnet-4-6")
async def handle_ticket(ticket: str):
    # Return the provider response object — token usage and cost are read
    # from response.usage. (Returning just the text records zero tokens.)
    return await client.messages.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": ticket}],
    )

response = await handle_ticket("My invoice is wrong")
answer = response.content[0].text
```

That's it. Every call is now tracked — duration, tokens, cost, errors — in a local
SQLite database at `~/.bifrost-monitor/runs.db`.

## CLI

```bash
# Recent runs
bifrost-monitor runs --last 24h

# Cost breakdown by model
bifrost-monitor costs --group-by model

# Error summary
bifrost-monitor errors --last 7d

# Full summary
bifrost-monitor summary --name support-agent
```

## Features

- **One-line decorator** — `@monitor()` wraps sync and async functions
- **Auto token extraction** — detects Anthropic and OpenAI response objects
- **Built-in pricing** — current Claude models (Fable 5, Opus 4.6–4.8, Sonnet 4.6/5, Haiku 4.5) plus GPT-4o/4.1 and Gemini 2.5, with cache-token pricing for Claude
- **Local SQLite storage** — zero config, `~/.bifrost-monitor/runs.db`
- **Rich CLI** — tables, colors, filtering by time/model/name
- **Export** — JSON and CSV export for further analysis
- **Custom models** — add your own pricing with `ModelPricing.add_model()`
- **Type-safe** — full type hints, pyright strict clean, Pydantic models

## Programmatic API

```python
from bifrost_monitor import MonitorTracker, TokenUsage

tracker = MonitorTracker()

# Manual recording
tracker.record(
    name="my-agent",
    model="claude-sonnet-4-6",
    token_usage=TokenUsage(input_tokens=500, output_tokens=200),
)

# Decorator
@tracker.monitor(name="my-agent", model="claude-sonnet-4-6")
def process(text: str) -> str:
    ...
```

## Custom Model Pricing

```python
from bifrost_monitor import ModelPricing

pricing = ModelPricing()
pricing.add_model("my-fine-tune", input_per_m=5.0, output_per_m=15.0)
```

## Development

```bash
git clone https://github.com/Jbermingham1/bifrost-monitor.git
cd bifrost-monitor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest  # 99 tests, 95% coverage
```

## License

MIT
