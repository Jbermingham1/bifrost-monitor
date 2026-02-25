# Contributing to bifrost-monitor

## Development Setup

```bash
git clone https://github.com/Jbermingham1/bifrost-monitor.git
cd bifrost-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                    # all tests with coverage
pytest tests/unit/        # unit tests only
pytest tests/integration/ # integration tests only
```

## Code Quality

```bash
ruff check src/ tests/    # lint
ruff format src/ tests/   # format
pyright                   # type check (strict mode)
bandit -r src/            # security scan
```

## TDD Workflow

1. Write a failing test
2. Write minimal code to pass
3. Refactor while tests stay green

## Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Coverage >= 80%
- [ ] Types pass (`pyright`)
- [ ] Linting passes (`ruff check`)
- [ ] CHANGELOG.md updated
