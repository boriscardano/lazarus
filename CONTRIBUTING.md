# Contributing to Lazarus

Thank you for your interest in contributing to Lazarus! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/lazarus.git`
3. Create a virtual environment: `uv venv && source .venv/bin/activate`
4. Install development dependencies: `uv pip install -e ".[dev]"`
5. Create a feature branch: `git checkout -b feature/your-feature-name`

## Development Setup

### Prerequisites

- Python 3.11+
- Claude Code installed and authenticated
- Git
- `gh` CLI

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lazarus --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run tests matching a pattern
pytest -k "test_healing"
```

### Code Style

We use the following tools for code quality:

- **ruff** for linting and formatting
- **mypy** for type checking

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type check
mypy src
```

## Making Changes

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `chore:` Maintenance tasks
- `test:` Adding or updating tests
- `refactor:` Code refactoring

Examples:
```
feat: add Discord notification support
fix: handle missing git config gracefully
docs: update configuration reference
```

### Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add tests for new functionality
4. Update CHANGELOG.md
5. Create a pull request with a clear description

### PR Title Format

Use the same format as commit messages:
```
feat: add support for custom success criteria
```

## Project Structure

```
lazarus/
├── src/lazarus/
│   ├── cli.py           # CLI entry points
│   ├── config/          # Configuration loading and validation
│   ├── core/            # Core healing logic
│   ├── claude/          # Claude Code integration
│   ├── git/             # Git operations and PR creation
│   ├── notifications/   # Notification dispatchers
│   ├── security/        # Secrets redaction
│   └── logging/         # Structured logging
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
└── docs/                # Documentation
```

## Adding New Features

### New Notification Channel

1. Create a new file in `src/lazarus/notifications/`
2. Implement the `NotificationChannel` protocol
3. Register in the dispatcher
4. Add configuration schema
5. Write tests
6. Update documentation

### New CLI Command

1. Add command function in `src/lazarus/cli.py`
2. Use Typer decorators for arguments
3. Write tests
4. Update CLI reference in README

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Claude Code version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (with secrets redacted)

## Questions?

Open a GitHub Discussion or Issue if you have questions about contributing.
