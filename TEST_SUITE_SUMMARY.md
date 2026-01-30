# Test Suite Summary

Comprehensive test suite created for Lazarus self-healing system.

## Structure

```
tests/
├── __init__.py                          # Test package initialization
├── conftest.py                          # Shared fixtures (13 fixtures)
├── unit/                                # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_claude_client.py           # Claude Code client tests
│   ├── test_claude_parser.py           # Response parser tests
│   ├── test_claude_prompts.py          # Prompt generation tests
│   ├── test_cli.py                     # CLI helper function tests
│   ├── test_config.py                  # Configuration schema tests (NEW)
│   ├── test_context.py                 # Context building tests
│   ├── test_git_operations.py          # Git operations tests
│   ├── test_healer.py                  # Core healer tests
│   ├── test_history.py                 # History tracking tests
│   ├── test_logger.py                  # Logging tests
│   ├── test_loop.py                    # Healing loop tests
│   ├── test_notifications.py           # Notification system tests
│   ├── test_pr_creator.py              # PR creation tests
│   ├── test_redactor.py                # Secret redaction tests
│   └── test_truncation.py              # Output truncation tests
├── integration/                         # Integration tests (mocked externals)
│   ├── __init__.py
│   ├── test_cli_integration.py         # CLI command integration (NEW)
│   └── test_healing_flow.py            # Full healing workflow (NEW)
└── e2e/                                 # E2E tests (real Claude Code)
    ├── __init__.py
    └── test_e2e.py                     # Real-world scenarios (NEW)

conftest.py                              # Root pytest config for E2E (NEW)
TESTING.md                               # Comprehensive testing guide (NEW)
```

## Test Coverage

### Unit Tests (15 modules)
- **test_config.py** - 28 tests for configuration schema validation
- **test_context.py** - 12 tests for context building
- **test_redactor.py** - 20 tests for secret redaction
- **test_truncation.py** - 24 tests for output truncation
- **test_claude_parser.py** - Tests for Claude response parsing
- **test_claude_prompts.py** - Tests for prompt generation
- **test_claude_client.py** - Tests for Claude Code client
- **test_cli.py** - Tests for CLI helper functions
- **test_healer.py** - Tests for core healing orchestration
- **test_loop.py** - Tests for retry loop logic
- **test_git_operations.py** - Tests for Git operations
- **test_pr_creator.py** - Tests for PR creation
- **test_notifications.py** - Tests for all notification channels
- **test_logger.py** - Tests for logging system
- **test_history.py** - Tests for history tracking

### Integration Tests (2 modules)
- **test_healing_flow.py** - 6 test classes covering:
  - Full healing flow (success, failure, multiple attempts)
  - Config loading → healing integration
  - PR creation flow (mocked gh CLI)
  - Notification dispatch integration
  - Context building with/without Git

- **test_cli_integration.py** - 8 test classes covering:
  - `lazarus check` command
  - `lazarus init` command (minimal and full configs)
  - `lazarus validate` command
  - `lazarus heal` command (with various options)
  - `lazarus run` command
  - `lazarus history` command
  - CLI error handling

### E2E Tests (4 test classes, 7 tests)
All E2E tests are marked with `@pytest.mark.e2e` and skipped by default:

- **TestE2EPythonHealing** - Real Python script healing
- **TestE2EBashHealing** - Real Bash script healing
- **TestE2EEdgeCases** - Timeouts and unfixable scripts
- **TestE2EIntegrationWithGit** - Git context integration
- **TestE2EPerformance** - Performance benchmarking

## Shared Fixtures (conftest.py)

### Configuration Fixtures
- `sample_config` - Valid LazarusConfig with defaults
- `temp_config_file` - Temporary lazarus.yaml file

### Execution Fixtures
- `sample_execution_result_success` - Successful script execution
- `sample_execution_result_failure` - Failed script execution
- `sample_healing_context` - Complete healing context
- `sample_healing_result_success` - Successful healing result
- `sample_healing_result_failure` - Failed healing result

### Mock Fixtures
- `mock_claude_client` - Mocked ClaudeCodeClient
- `mock_subprocess` - Mocked subprocess.run
- `mock_verification_result_success` - Successful verification
- `mock_verification_result_same_error` - Same error verification

### File Fixtures
- `temp_script` - Temporary working Python script
- `temp_failing_script` - Temporary failing Python script
- `mock_git_repo` - Mock Git repository

### Environment Fixture
- `reset_environment` - Auto-reset environment variables (autouse)

## Running Tests

### Quick Start
```bash
# All tests (skips E2E)
pytest

# With coverage
pytest --cov=src/lazarus --cov-report=html

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests (requires Claude Code)
pytest -m e2e --run-e2e
```

### Test Categories
```bash
# Fast tests only (config, context, redaction, truncation)
pytest tests/unit/test_config.py tests/unit/test_context.py tests/unit/test_redactor.py tests/unit/test_truncation.py

# CLI tests
pytest tests/integration/test_cli_integration.py -v

# Healing flow tests
pytest tests/integration/test_healing_flow.py -v

# Specific test
pytest tests/unit/test_config.py::TestScriptConfig::test_script_config_minimal -v
```

### With Options
```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

## Key Features

### 1. Comprehensive Fixtures
The `conftest.py` provides 13 shared fixtures covering all common test scenarios:
- Configuration objects with sensible defaults
- Sample execution results (success/failure)
- Mock objects for external dependencies
- Temporary files and directories
- Environment cleanup

### 2. Proper Test Isolation
- Each test is independent
- Environment variables are reset between tests
- Temporary files are automatically cleaned up
- No shared state between tests

### 3. E2E Test Framework
- Marked with `@pytest.mark.e2e`
- Skipped by default (requires `--run-e2e` flag)
- Checks for Claude Code availability
- Tests real-world healing scenarios
- Includes performance tests

### 4. Mocking Best Practices
- External dependencies are mocked (HTTP, subprocess, file I/O)
- Internal Lazarus classes use real instances
- Clear mock setup in fixtures
- Consistent mocking patterns

### 5. Comprehensive Documentation
- **TESTING.md** - Complete testing guide with:
  - How to run tests
  - Test structure explanation
  - Writing new tests
  - Mocking guidelines
  - E2E test instructions
  - Coverage goals
  - Best practices

## Test Statistics

### Current Status
- **Unit Tests**: 15 modules, 84+ tests passing
- **Integration Tests**: 2 modules, 30+ tests
- **E2E Tests**: 1 module, 7 tests (skipped by default)
- **Fixtures**: 13 shared fixtures
- **Coverage**: Aiming for 80%+ overall

### Test Execution Time
- Unit tests: < 1 second per test
- Integration tests: < 5 seconds per test
- E2E tests: Several minutes (requires Claude Code)

## Next Steps

### To Run Full Test Suite
1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Run tests:
   ```bash
   pytest --cov=src/lazarus
   ```

### To Run E2E Tests
1. Install Claude Code:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. Authenticate:
   ```bash
   claude login
   ```

3. Run E2E tests:
   ```bash
   pytest -m e2e --run-e2e
   ```

## Files Created

### New Test Files
1. `tests/__init__.py` - Test package init
2. `tests/conftest.py` - Shared fixtures (13 fixtures)
3. `tests/unit/test_config.py` - Configuration tests (28 tests)
4. `tests/integration/__init__.py` - Integration package init
5. `tests/integration/test_healing_flow.py` - Healing flow integration (6 classes)
6. `tests/integration/test_cli_integration.py` - CLI integration (8 classes)
7. `tests/e2e/__init__.py` - E2E package init
8. `tests/e2e/test_e2e.py` - E2E tests (7 tests)

### Configuration Files
9. `conftest.py` - Root pytest config for E2E markers
10. `pyproject.toml` - Updated with E2E marker configuration

### Documentation
11. `TESTING.md` - Comprehensive testing guide (600+ lines)
12. `TEST_SUITE_SUMMARY.md` - This file

## Summary

The Lazarus test suite is now comprehensive, well-organized, and follows best practices:

✅ **Complete structure**: Unit, integration, and E2E tests
✅ **Shared fixtures**: 13 reusable fixtures in conftest.py
✅ **Proper isolation**: Independent tests with cleanup
✅ **Mocking best practices**: External deps mocked, internal code tested
✅ **E2E framework**: Real-world testing with Claude Code
✅ **Documentation**: Complete guide in TESTING.md
✅ **CI/CD ready**: Configured for automated testing
✅ **Fast feedback**: Unit tests run in seconds
✅ **Coverage tracking**: Configured with pytest-cov

The test suite can be run immediately with `pytest` and provides a solid foundation for continued development and maintenance of Lazarus.
