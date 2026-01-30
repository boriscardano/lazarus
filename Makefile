.PHONY: help install install-dev test lint format typecheck clean build publish

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install lazarus
	uv pip install -e .

install-dev:  ## Install lazarus with dev dependencies
	uv pip install -e ".[dev]"

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov=src/lazarus --cov-report=term --cov-report=html

test-e2e:  ## Run E2E tests (requires Claude Code)
	LAZARUS_RUN_E2E=1 uv run pytest tests/e2e/ -v

lint:  ## Run linting
	uv run ruff check src tests

lint-fix:  ## Run linting with auto-fix
	uv run ruff check --fix src tests

format:  ## Format code
	uv run ruff format src tests

format-check:  ## Check code formatting
	uv run ruff format --check src tests

typecheck:  ## Run type checking
	uv run mypy src

check:  ## Run all checks (lint, format, typecheck)
	@echo "Running linting..."
	uv run ruff check src tests
	@echo "Checking formatting..."
	uv run ruff format --check src tests
	@echo "Running type checking..."
	uv run mypy src
	@echo "All checks passed!"

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:  ## Build package
	uv build

publish:  ## Publish to PyPI (requires authentication)
	uv publish
