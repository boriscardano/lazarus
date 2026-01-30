"""Tests for the Healer class and healing orchestration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from lazarus.config.schema import HealingConfig, LazarusConfig
from lazarus.core.context import ExecutionResult
from lazarus.core.healer import Healer, HealingAttempt, HealingResult
from lazarus.core.verification import ErrorComparison, VerificationResult


@pytest.fixture
def basic_config():
    """Create a basic Lazarus configuration for testing."""
    return LazarusConfig(
        scripts=[],
        healing=HealingConfig(
            max_attempts=3,
            timeout_per_attempt=300,
            total_timeout=900,
        ),
    )


@pytest.fixture
def mock_script_path(tmp_path):
    """Create a temporary script file for testing."""
    script = tmp_path / "test_script.py"
    script.write_text("print('Hello, world!')\n")
    return script


def test_healer_initialization(basic_config):
    """Test that Healer can be initialized with a config."""
    healer = Healer(basic_config)

    assert healer.config == basic_config
    assert healer.runner is not None
    assert healer.loop is not None
    assert healer.loop.max_attempts == 3


def test_healer_script_not_found(basic_config):
    """Test that Healer raises FileNotFoundError for non-existent script."""
    healer = Healer(basic_config)

    with pytest.raises(FileNotFoundError):
        healer.heal(Path("/nonexistent/script.py"))


def test_healer_success_on_first_run(basic_config, mock_script_path):
    """Test that Healer returns success if script succeeds on first run."""
    healer = Healer(basic_config)

    # Mock the script runner to return success
    with patch.object(healer.runner, 'run_script') as mock_run:
        mock_run.return_value = ExecutionResult(
            exit_code=0,
            stdout="Success!",
            stderr="",
            duration=1.0,
        )

        result = healer.heal(mock_script_path)

        assert result.success is True
        assert len(result.attempts) == 0
        assert result.final_execution.exit_code == 0


def test_healer_finds_script_config(basic_config, mock_script_path):
    """Test that Healer can find script configuration by name."""
    from lazarus.config.schema import ScriptConfig

    # Add a script config
    basic_config.scripts.append(
        ScriptConfig(
            name="test_script",
            path=mock_script_path,
            timeout=600,
        )
    )

    healer = Healer(basic_config)
    found_config = healer._find_script_config(mock_script_path)

    assert found_config is not None
    assert found_config.name == "test_script"
    assert found_config.timeout == 600


def test_healer_no_script_config_found(basic_config, mock_script_path):
    """Test that Healer returns None when no script config matches."""
    healer = Healer(basic_config)
    found_config = healer._find_script_config(mock_script_path)

    assert found_config is None


def test_healing_result_dataclass():
    """Test that HealingResult can be created properly."""
    result = HealingResult(
        success=True,
        attempts=[],
        final_execution=ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
        ),
        pr_url="https://github.com/owner/repo/pull/123",
        duration=5.0,
    )

    assert result.success is True
    assert result.pr_url == "https://github.com/owner/repo/pull/123"
    assert result.duration == 5.0
    assert result.error_message is None


def test_healing_attempt_dataclass():
    """Test that HealingAttempt can be created properly."""
    from lazarus.claude.parser import ClaudeResponse

    attempt = HealingAttempt(
        attempt_number=1,
        claude_response=ClaudeResponse(
            success=True,
            explanation="Fixed the bug",
            files_changed=["script.py"],
            error_message=None,
            raw_output="",
        ),
        verification=VerificationResult(
            status="success",
            execution_result=ExecutionResult(
                exit_code=0,
                stdout="",
                stderr="",
                duration=1.0,
            ),
            comparison=ErrorComparison(
                is_same_error=False,
                similarity_score=0.0,
                key_differences=[],
            ),
            custom_criteria_passed=None,
        ),
        duration=30.0,
    )

    assert attempt.attempt_number == 1
    assert attempt.claude_response.success is True
    assert attempt.verification.status == "success"
    assert attempt.duration == 30.0


def test_has_uncommitted_changes_no_git(basic_config, tmp_path):
    """Test that _has_uncommitted_changes returns False when not in git repo."""
    healer = Healer(basic_config)
    script = tmp_path / "script.py"
    script.write_text("print('test')")

    # Should return False (no git repo)
    has_changes = healer._has_uncommitted_changes(script)
    assert has_changes is False
