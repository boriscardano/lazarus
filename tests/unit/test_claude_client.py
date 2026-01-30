"""Unit tests for Claude Code CLI client."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lazarus.claude.client import ClaudeCodeClient
from lazarus.config.schema import HealingConfig, LazarusConfig
from lazarus.core.context import ExecutionResult, HealingContext, SystemContext


@pytest.fixture
def temp_working_dir(tmp_path):
    """Create a temporary working directory."""
    return tmp_path


@pytest.fixture
def test_context(temp_working_dir):
    """Create a test healing context."""
    script_path = temp_working_dir / "script.py"
    script_path.write_text("print('hello')\n")

    return HealingContext(
        script_path=script_path,
        script_content="print('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="SyntaxError",
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=temp_working_dir,
        ),
        config=LazarusConfig(),
    )


def test_client_initialization(temp_working_dir):
    """Test client initialization."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    assert client.working_dir == temp_working_dir.resolve()
    assert client.timeout == 300


def test_client_initialization_invalid_dir():
    """Test client initialization with invalid directory."""
    with pytest.raises(ValueError, match="does not exist"):
        ClaudeCodeClient(working_dir=Path("/nonexistent/path"))


def test_is_available():
    """Test checking if Claude CLI is available."""
    client = ClaudeCodeClient(working_dir=Path.cwd(), timeout=300)

    # Result depends on whether claude is actually installed
    result = client.is_available()
    assert isinstance(result, bool)


@patch("shutil.which")
def test_is_available_mocked(mock_which, temp_working_dir):
    """Test checking availability with mocked which."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # Test when claude is available
    mock_which.return_value = "/usr/local/bin/claude"
    assert client.is_available()

    # Test when claude is not available
    mock_which.return_value = None
    assert not client.is_available()


@patch("subprocess.run")
@patch("shutil.which")
def test_get_version(mock_which, mock_run, temp_working_dir):
    """Test getting Claude Code version."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # Test when claude is available
    mock_which.return_value = "/usr/local/bin/claude"
    mock_run.return_value = MagicMock(
        returncode=0, stdout="claude 1.2.3\n", stderr=""
    )

    version = client.get_version()
    assert version == "1.2.3"

    # Test when claude is not available
    mock_which.return_value = None
    version = client.get_version()
    assert version is None


@patch("subprocess.run")
def test_request_fix_not_available(mock_run, temp_working_dir, test_context):
    """Test request_fix when Claude CLI is not available."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    with patch.object(client, "is_available", return_value=False):
        with pytest.raises(RuntimeError, match="not available"):
            client.request_fix(test_context)


@patch("subprocess.run")
def test_request_fix_success(mock_run, temp_working_dir, test_context):
    """Test successful fix request."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # Mock successful Claude Code execution
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="I've fixed the issue. Edit[file_path='script.py']",
        stderr="",
    )

    with patch.object(client, "is_available", return_value=True):
        response = client.request_fix(test_context)

    assert response.success
    assert len(response.files_changed) > 0
    assert response.error_message is None


@patch("subprocess.run")
def test_request_fix_timeout(mock_run, temp_working_dir, test_context):
    """Test fix request timeout."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=10)

    # Mock timeout
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=["claude"], timeout=10, output=b"", stderr=b""
    )

    with patch.object(client, "is_available", return_value=True):
        response = client.request_fix(test_context)

    assert not response.success
    assert "timed out" in response.error_message.lower()


@patch("subprocess.run")
def test_request_fix_subprocess_error(mock_run, temp_working_dir, test_context):
    """Test fix request with subprocess error."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # Mock subprocess error
    mock_run.side_effect = subprocess.SubprocessError("Command failed")

    with patch.object(client, "is_available", return_value=True):
        response = client.request_fix(test_context)

    assert not response.success
    assert response.error_message is not None


def test_get_allowed_tools_default(temp_working_dir, test_context):
    """Test getting default allowed tools."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    tools = client._get_allowed_tools(test_context)

    assert "Edit" in tools
    assert "Read" in tools
    assert "Write" in tools


def test_get_allowed_tools_from_config(temp_working_dir):
    """Test getting allowed tools from config."""
    config = LazarusConfig(
        healing=HealingConfig(allowed_tools=["Edit", "Read"])
    )

    context = HealingContext(
        script_path=Path("script.py"),
        script_content="",
        execution_result=ExecutionResult(
            exit_code=1, stdout="", stderr="", duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path.cwd(),
        ),
        config=config,
    )

    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)
    tools = client._get_allowed_tools(context)

    assert tools == ["Edit", "Read"]


def test_get_allowed_tools_with_forbidden(temp_working_dir):
    """Test getting allowed tools with forbidden tools."""
    config = LazarusConfig(
        healing=HealingConfig(forbidden_tools=["Bash"])
    )

    context = HealingContext(
        script_path=Path("script.py"),
        script_content="",
        execution_result=ExecutionResult(
            exit_code=1, stdout="", stderr="", duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path.cwd(),
        ),
        config=config,
    )

    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)
    tools = client._get_allowed_tools(context)

    assert "Bash" not in tools
    assert "Edit" in tools


@patch("subprocess.run")
def test_request_fix_with_retry_success_first_attempt(
    mock_run, temp_working_dir, test_context
):
    """Test retry with success on first attempt."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Fixed! Edit[file_path='script.py']",
        stderr="",
    )

    with patch.object(client, "is_available", return_value=True):
        response, attempts = client.request_fix_with_retry(test_context, max_attempts=3)

    assert response.success
    assert attempts == 1


@patch("subprocess.run")
def test_request_fix_with_retry_success_second_attempt(
    mock_run, temp_working_dir, test_context
):
    """Test retry with success on second attempt."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # First call fails, second succeeds
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="Couldn't fix it", stderr=""),
        MagicMock(returncode=0, stdout="Fixed! Edit[file_path='script.py']", stderr=""),
    ]

    with patch.object(client, "is_available", return_value=True):
        response, attempts = client.request_fix_with_retry(test_context, max_attempts=3)

    assert response.success
    assert attempts == 2


@patch("subprocess.run")
def test_request_fix_with_retry_all_attempts_fail(
    mock_run, temp_working_dir, test_context
):
    """Test retry with all attempts failing."""
    client = ClaudeCodeClient(working_dir=temp_working_dir, timeout=300)

    # All calls fail
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Couldn't fix it", stderr=""
    )

    with patch.object(client, "is_available", return_value=True):
        response, attempts = client.request_fix_with_retry(test_context, max_attempts=3)

    assert not response.success
    assert attempts == 3
