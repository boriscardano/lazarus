"""Shared pytest fixtures for Lazarus tests.

This module provides common fixtures used across unit, integration,
and e2e tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lazarus.config.schema import (
    HealingConfig,
    LazarusConfig,
    LoggingConfig,
    ScriptConfig,
)
from lazarus.core.context import ExecutionResult, HealingContext, SystemContext
from lazarus.core.healer import HealingResult
from lazarus.core.verification import ErrorComparison, VerificationResult


@pytest.fixture
def sample_config() -> LazarusConfig:
    """Create a valid LazarusConfig fixture for testing.

    Returns:
        LazarusConfig with sensible defaults
    """
    return LazarusConfig(
        scripts=[
            ScriptConfig(
                name="test-script",
                path=Path("scripts/test.py"),
                description="Test script",
                timeout=300,
            )
        ],
        healing=HealingConfig(
            max_attempts=3,
            timeout_per_attempt=300,
            total_timeout=900,
            claude_model="claude-sonnet-4-5-20250929",
        ),
        logging=LoggingConfig(
            level="INFO",
            console=True,
        ),
    )


@pytest.fixture
def sample_execution_result_success() -> ExecutionResult:
    """Create a successful ExecutionResult fixture.

    Returns:
        ExecutionResult with exit code 0
    """
    return ExecutionResult(
        exit_code=0,
        stdout="Test completed successfully",
        stderr="",
        duration=1.5,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_execution_result_failure() -> ExecutionResult:
    """Create a failed ExecutionResult fixture.

    Returns:
        ExecutionResult with exit code 1
    """
    return ExecutionResult(
        exit_code=1,
        stdout="Test output",
        stderr="Error: Something went wrong\nTraceback (most recent call last):\n  File 'test.py', line 10\n    x = undefined_var\nNameError: name 'undefined_var' is not defined",
        duration=0.5,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_healing_context(
    sample_config: LazarusConfig,
    sample_execution_result_failure: ExecutionResult,
    tmp_path: Path,
) -> HealingContext:
    """Create a HealingContext fixture.

    Args:
        sample_config: LazarusConfig fixture
        sample_execution_result_failure: Failed ExecutionResult
        tmp_path: pytest tmp_path fixture

    Returns:
        HealingContext for testing
    """
    # Create a test script
    script_path = tmp_path / "test_script.py"
    script_path.write_text("#!/usr/bin/env python3\nprint('Hello')\n")

    return HealingContext(
        script_path=script_path,
        script_content=script_path.read_text(),
        execution_result=sample_execution_result_failure,
        git_context=None,  # No git context in tmp_path
        system_context=SystemContext(
            os_name="Linux",
            os_version="5.15.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=tmp_path,
        ),
        config=sample_config,
    )


@pytest.fixture
def sample_healing_result_success(
    sample_execution_result_success: ExecutionResult,
) -> HealingResult:
    """Create a successful HealingResult fixture.

    Args:
        sample_execution_result_success: Successful ExecutionResult

    Returns:
        HealingResult indicating success
    """
    return HealingResult(
        success=True,
        attempts=[],
        final_execution=sample_execution_result_success,
        pr_url="https://github.com/test/repo/pull/123",
        duration=5.0,
        error_message=None,
    )


@pytest.fixture
def sample_healing_result_failure(
    sample_execution_result_failure: ExecutionResult,
) -> HealingResult:
    """Create a failed HealingResult fixture.

    Args:
        sample_execution_result_failure: Failed ExecutionResult

    Returns:
        HealingResult indicating failure
    """
    return HealingResult(
        success=False,
        attempts=[],
        final_execution=sample_execution_result_failure,
        pr_url=None,
        duration=10.0,
        error_message="Failed to heal after 3 attempts",
    )


@pytest.fixture
def mock_claude_client():
    """Create a mocked ClaudeCodeClient.

    Returns:
        Mock ClaudeCodeClient with pre-configured responses
    """
    with patch("lazarus.claude.client.ClaudeCodeClient") as mock_client:
        # Configure the mock
        mock_instance = Mock()
        mock_instance.is_available.return_value = True
        mock_instance.request_fix.return_value = Mock(
            success=True,
            explanation="Fixed the undefined variable issue",
            files_changed=["test.py"],
            error_message=None,
            raw_output="Claude Code output",
        )
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def temp_script(tmp_path: Path) -> Path:
    """Create a temporary test script.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to the created script
    """
    script = tmp_path / "test_script.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys

def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    )
    script.chmod(0o755)
    return script


@pytest.fixture
def temp_failing_script(tmp_path: Path) -> Path:
    """Create a temporary failing test script.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to the created failing script
    """
    script = tmp_path / "failing_script.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys

def main():
    # This will fail with NameError
    print(undefined_variable)
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    )
    script.chmod(0o755)
    return script


@pytest.fixture
def temp_config_file(tmp_path: Path, temp_script: Path) -> Path:
    """Create a temporary lazarus.yaml configuration file.

    Args:
        tmp_path: pytest tmp_path fixture
        temp_script: Temporary script path

    Returns:
        Path to the created config file
    """
    config_file = tmp_path / "lazarus.yaml"
    config_content = f"""
scripts:
  - name: test-script
    path: {temp_script}
    description: Test script
    timeout: 300

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900

git:
  create_pr: true
  branch_prefix: lazarus/fix

logging:
  level: INFO
  console: true
"""
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing external commands.

    Yields:
        Mock subprocess.run function
    """
    with patch("subprocess.run") as mock_run:
        # Default: successful command execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_git_repo(tmp_path: Path) -> Path:
    """Create a mock git repository for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to the git repository root
    """
    repo_path = tmp_path / "git_repo"
    repo_path.mkdir()

    # Create .git directory
    git_dir = repo_path / ".git"
    git_dir.mkdir()

    # Create a test file
    test_file = repo_path / "test.py"
    test_file.write_text("print('test')")

    return repo_path


@pytest.fixture
def mock_verification_result_success(
    sample_execution_result_success: ExecutionResult,
) -> VerificationResult:
    """Create a successful VerificationResult fixture.

    Args:
        sample_execution_result_success: Successful ExecutionResult

    Returns:
        VerificationResult indicating success
    """
    return VerificationResult(
        status="success",
        execution_result=sample_execution_result_success,
        comparison=ErrorComparison(
            is_same_error=False,
            similarity_score=0.0,
            key_differences=["Script now succeeds"],
        ),
        custom_criteria_passed=None,
    )


@pytest.fixture
def mock_verification_result_same_error(
    sample_execution_result_failure: ExecutionResult,
) -> VerificationResult:
    """Create a VerificationResult with same error.

    Args:
        sample_execution_result_failure: Failed ExecutionResult

    Returns:
        VerificationResult indicating same error
    """
    return VerificationResult(
        status="same_error",
        execution_result=sample_execution_result_failure,
        comparison=ErrorComparison(
            is_same_error=True,
            similarity_score=0.95,
            key_differences=[],
        ),
        custom_criteria_passed=None,
    )


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test.

    This fixture automatically runs before each test to ensure
    a clean environment.
    """
    # Store original environment
    import os
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
