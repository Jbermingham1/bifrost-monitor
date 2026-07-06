# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-07-06

### Fixed
- **Default storage now actually persists.** `MonitorTracker()` (and the module-level
  `monitor`/`record` helpers) previously defaulted to an in-memory store — runs
  recorded via the documented quickstart never reached the SQLite database the CLI
  reads. The default store is now `SQLiteStore` at `~/.bifrost-monitor/runs.db`,
  as documented. Pass `InMemoryStore()` explicitly for ephemeral tracking.
- **Model prices corrected and updated** against provider pricing pages (2026-07):
  Claude Opus was priced 3x too high, Haiku 4.5 and Gemini 2.5 Flash were wrong.
  Added current Claude models (Fable 5, Opus 4.7/4.8, Sonnet 5) with cache
  read/write pricing; removed non-existent alias model IDs.
- Quickstart example returned the response text, which auto-extraction cannot read
  token usage from — it now returns the response object, and the docs say why.
- README comparison table no longer asserts competitor prices; install instructions
  now use the working source install; release date corrected below.
- Author email corrected.

## [0.1.0] - 2026-02-12

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
