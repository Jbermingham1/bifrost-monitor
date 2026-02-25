# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-06-01

### Added
- `@monitor()` decorator for sync and async functions
- Automatic token usage extraction from Anthropic and OpenAI responses
- Built-in pricing for Claude 4.5/4.6, GPT-4o, GPT-4.1, Gemini 2.5
- SQLite local storage (zero-config, `~/.bifrost-monitor/runs.db`)
- CLI commands: `runs`, `costs`, `errors`, `summary`
- Time-based filtering (`--last 24h`, `--last 7d`)
- JSON and CSV export
- Custom model pricing support
- 99 tests, 95% coverage
