# bifrost-monitor

[![CI](https://github.com/Jbermingham1/bifrost-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Jbermingham1/bifrost-monitor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/bifrost-monitor.svg)](https://pypi.org/project/bifrost-monitor/)

**Zero-config AI agent observability.** One decorator. Local SQLite. Instant insights.

No SaaS account. No API proxy. No infrastructure. Just `pip install` and one line of code.

## Why?

| Tool | Setup | Cost | Data |
|------|-------|------|------|
| LangSmith | Account + API key + proxy | $400/mo+ | Their cloud |
| Helicone | Account + API proxy | $50/mo+ | Their cloud |
| **bifrost-monitor** | `pip install` | **Free** | **Your machine** |

## Quick Start

```bash
pip install bifrost-monitor
```

```python
from bifrost_monitor import monitor

@monitor(name="support-agent", model="claude-sonnet-4-6")
async def handle_ticket(ticket: str) -> str:
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": ticket}],
    )
    return response.content[0].text
```

That's it. Every call is now tracked — duration, tokens, cost, errors — all in a local SQLite database.

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
- **Built-in pricing** — Claude 4.5/4.6, GPT-4o, GPT-4.1, Gemini 2.5
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
