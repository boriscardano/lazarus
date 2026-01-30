# Testing Guide for Lazarus

This document explains how to run tests, understand the test structure, write new tests, and follow best practices for testing Lazarus.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing New Tests](#writing-new-tests)
- [Mocking Guidelines](#mocking-guidelines)
- [E2E Tests](#e2e-tests)
- [Coverage](#coverage)
- [Continuous Integration](#continuous-integration)

## Quick Start

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src/lazarus --cov-report=html
```

Run specific test category:
```bash
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest -m e2e --run-e2e     # E2E tests (requires Claude Code)
```

## Test Structure

The test suite is organized into three categories:

```
tests/
├── __init__.py                  # Test package init
├── conftest.py                  # Shared fixtures for all tests
├── unit/                        # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_claude_client.py
│   ├── test_claude_parser.py
│   ├── test_claude_prompts.py
│   ├── test_config.py
│   ├── test_context.py
│   ├── test_healer.py
│   ├── test_history.py
│   ├── test_logger.py
│   ├── test_loop.py
│   ├── test_notifications.py
│   ├── test_redactor.py
│   └── test_truncation.py
├── integration/                 # Integration tests (multiple components)
│   ├── __init__.py
│   ├── test_cli_integration.py
│   └── test_healing_flow.py
└── e2e/                        # End-to-end tests (real Claude Code)
    ├── __init__.py
    └── test_e2e.py
```

### Unit Tests

Unit tests focus on individual components in isolation:
- **Fast execution** (typically < 1 second per test)
- **No external dependencies** (everything mocked)
- **High coverage** of edge cases and error conditions
- **Deterministic** (same input always produces same output)

### Integration Tests

Integration tests verify multiple components working together:
- **Mocked external services** (Claude Code API, gh CLI, notifications)
- **Real internal interactions** between Lazarus components
- **Tests full workflows** like config → context → healing → PR
- **Moderate execution time** (typically < 5 seconds per test)

### E2E Tests

End-to-end tests use actual Claude Code and external services:
- **Requires Claude Code CLI** installed and authenticated
- **Network access** to Claude API
- **Skipped by default** (run with `--run-e2e` flag)
- **Slower execution** (can take minutes)
- **Tests real-world scenarios** with actual fixes

## Running Tests

### Basic Commands

```bash
# Run all tests (skips E2E by default)
pytest

# Run with verbose output
pytest -v

# Run with detailed output
pytest -vv

# Stop on first failure
pytest -x

# Run specific test file
pytest tests/unit/test_healer.py

# Run specific test function
pytest tests/unit/test_healer.py::test_healer_initialization

# Run tests matching a pattern
pytest -k "test_heal"
```

### Running by Category

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests (requires --run-e2e flag)
pytest tests/e2e/ --run-e2e
pytest -m e2e --run-e2e
```

### Output Control

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Full traceback
pytest --tb=long

# Short traceback
pytest --tb=short

# No capture (see output in real-time)
pytest --capture=no
```

### Parallel Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

## Writing New Tests

### Test File Structure

```python
"""Module docstring describing what is being tested."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from lazarus.module import ClassToTest


class TestClassName:
    """Tests for ClassName."""

    def test_basic_functionality(self):
        """Test basic operation with valid input."""
        instance = ClassToTest()
        result = instance.method(valid_input)

        assert result == expected_output

    def test_edge_case(self):
        """Test behavior with edge case input."""
        instance = ClassToTest()
        result = instance.method(edge_case_input)

        assert result == expected_edge_output

    def test_error_handling(self):
        """Test error handling for invalid input."""
        instance = ClassToTest()

        with pytest.raises(ValueError, match="expected error"):
            instance.method(invalid_input)
```

### Using Fixtures

Fixtures are defined in `tests/conftest.py` and automatically available:

```python
def test_with_fixtures(sample_config, temp_script):
    """Test using shared fixtures."""
    # sample_config is a valid LazarusConfig
    # temp_script is a temporary Python script

    healer = Healer(sample_config)
    result = healer.heal(temp_script)

    assert result is not None
```

Available fixtures:
- `sample_config` - Valid LazarusConfig
- `sample_execution_result_success` - Successful ExecutionResult
- `sample_execution_result_failure` - Failed ExecutionResult
- `sample_healing_context` - HealingContext fixture
- `sample_healing_result_success` - Successful HealingResult
- `sample_healing_result_failure` - Failed HealingResult
- `mock_claude_client` - Mocked ClaudeCodeClient
- `temp_script` - Temporary test script
- `temp_failing_script` - Temporary failing script
- `temp_config_file` - Temporary lazarus.yaml
- `mock_subprocess` - Mocked subprocess.run
- `mock_git_repo` - Mock git repository

### Parametrized Tests

Test multiple inputs with one test function:

```python
@pytest.mark.parametrize("input,expected", [
    ("case1", "result1"),
    ("case2", "result2"),
    ("case3", "result3"),
])
def test_multiple_cases(input, expected):
    """Test multiple input/output combinations."""
    result = function_under_test(input)
    assert result == expected
```

### Async Tests

For testing async functions:

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function_under_test(input)
    assert result == expected
```

## Mocking Guidelines

### When to Mock

Mock external dependencies and I/O operations:
- ✅ Mock: HTTP requests, subprocess calls, file I/O (when not critical)
- ✅ Mock: Claude Code API, GitHub CLI, notification services
- ❌ Don't mock: Internal Lazarus classes (in unit tests, use real instances)
- ❌ Don't mock: Built-in Python functions unless necessary

### Mocking with unittest.mock

```python
from unittest.mock import Mock, patch, MagicMock

# Mock a function return value
def test_with_mock():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked value"

        result = code_that_calls_function()

        assert result == "mocked value"
        mock_func.assert_called_once()

# Mock a class
def test_with_mock_class():
    with patch('module.ClassName') as MockClass:
        mock_instance = Mock()
        MockClass.return_value = mock_instance

        instance = ClassName()
        instance.method()

        mock_instance.method.assert_called_once()

# Mock subprocess
def test_subprocess_call():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        result = function_that_calls_subprocess()

        assert result is not None
```

### Mocking HTTP Requests

```python
def test_http_request():
    with patch('httpx.Client') as mock_client:
        # Mock the context manager and post method
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = function_that_makes_http_request()

        assert result is True
```

### Mocking Environment Variables

```python
def test_with_env_var(monkeypatch):
    """Test with environment variable."""
    monkeypatch.setenv("TEST_VAR", "test_value")

    result = function_that_uses_env_var()

    assert result == "test_value"
```

## E2E Tests

E2E tests are skipped by default because they require:
- Claude Code CLI installed: `npm install -g @anthropic-ai/claude-code`
- Authentication: `claude login`
- Network access to Claude API
- Longer execution time (minutes vs seconds)

### Running E2E Tests

```bash
# Check if Claude Code is available
claude --version

# Authenticate if needed
claude login

# Run E2E tests
pytest -m e2e --run-e2e

# Run specific E2E test
pytest tests/e2e/test_e2e.py::test_heal_simple_python_error --run-e2e
```

### Writing E2E Tests

E2E tests should be marked with `@pytest.mark.e2e` and `@pytest.mark.skip`:

```python
import pytest

@pytest.mark.e2e
@pytest.mark.skip(reason="Requires Claude Code CLI and API access")
def test_e2e_scenario(check_claude_available, e2e_config):
    """E2E test with actual Claude Code.

    This test requires --run-e2e flag to run.
    """
    healer = Healer(e2e_config)
    result = healer.heal(broken_script)

    assert result.success is True
```

## Coverage

### Generating Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src/lazarus

# Generate HTML report
pytest --cov=src/lazarus --cov-report=html

# Open HTML report
open htmlcov/index.html

# Show missing lines
pytest --cov=src/lazarus --cov-report=term-missing

# Fail if coverage is below threshold
pytest --cov=src/lazarus --cov-fail-under=80
```

### Coverage Goals

- **Overall:** Aim for 80%+ coverage
- **Core modules:** 90%+ coverage (healer, loop, context)
- **CLI:** 70%+ coverage (harder to test UI)
- **New code:** All new code should include tests

### Viewing Coverage

After running `pytest --cov=src/lazarus --cov-report=html`:

1. Open `htmlcov/index.html` in browser
2. Click on any file to see line-by-line coverage
3. Red lines are not covered by tests
4. Green lines are covered

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Every push to any branch
- Every pull request
- Daily scheduled runs (for E2E tests)

See `.github/workflows/test.yml` for configuration.

### Pre-commit Hooks

Install pre-commit hooks to run tests before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version matches CI (3.11+)
- Ensure all dependencies are installed: `pip install -e ".[dev]"`
- Clear pytest cache: `pytest --cache-clear`

### Flaky Tests

If a test fails intermittently:
- Check for race conditions in async code
- Ensure tests don't depend on order
- Mock time-dependent operations
- Use `pytest-repeat` to reproduce: `pytest --count=10 test_file.py`

### Slow Tests

- Profile tests: `pytest --durations=10`
- Mock I/O operations
- Use smaller test data
- Consider moving slow tests to integration/E2E

### Import Errors

```bash
# Install package in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=/path/to/lazarus/src:$PYTHONPATH
```

## Best Practices

### Do's

- ✅ Write tests for new features before implementation (TDD)
- ✅ Test edge cases and error conditions
- ✅ Use descriptive test names
- ✅ Keep tests independent (no shared state)
- ✅ Mock external dependencies
- ✅ Use fixtures for common setup
- ✅ Test one thing per test (when practical)

### Don'ts

- ❌ Don't test implementation details
- ❌ Don't use `sleep()` in tests (mock time instead)
- ❌ Don't share state between tests
- ❌ Don't ignore failing tests
- ❌ Don't skip tests without a good reason
- ❌ Don't write tests that depend on external services (except E2E)

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
