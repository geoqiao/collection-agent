# Development Guide

## Environment Setup

This project uses [uv](https://github.com/astral-sh/uv) as the Python package manager.

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Install Dependencies

```bash
uv sync
```

### Run Tests

```bash
uv run pytest tests/ -v
```

### Run Linter

```bash
uv run ruff check src/ tests/
uv run ruff check src/ tests/ --fix
```

### Add Dependencies

```bash
uv add <package>
```

### Add Dev Dependencies

```bash
uv add --dev <package>
```

## Project Structure

```
collect-agent/
├── src/              # Source code
├── tests/            # Test suite
├── docs/             # Documentation
├── config.yaml       # Runtime configuration
├── pyproject.toml    # Project metadata and dependencies
└── uv.lock           # Locked dependency versions (managed by uv)
```

## Coding Standards

- Use `uv run` prefix for all Python commands
- Do not edit `uv.lock` manually
- All code must pass `ruff check`
- All tests must pass before merging
