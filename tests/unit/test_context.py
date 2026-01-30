"""Unit tests for context building functionality."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lazarus.config.schema import LazarusConfig
from lazarus.core.context import (
    ExecutionResult,
    GitContext,
    SystemContext,
    build_context,
    get_git_context,
    get_system_context,
)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_execution_result_success(self):
        """Test successful execution result."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.5,
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Success"
        assert result.stderr == ""
        assert result.duration == 1.5
        assert isinstance(result.timestamp, datetime)

    def test_execution_result_failure(self):
        """Test failed execution result."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error occurred",
            duration=0.5,
        )
        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Error occurred"

    def test_execution_result_custom_timestamp(self):
        """Test execution result with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
            timestamp=custom_time,
        )
        assert result.timestamp == custom_time


class TestSystemContext:
    """Tests for get_system_context function."""

    @patch("platform.system")
    @patch("platform.version")
    @patch("os.environ.get")
    @patch("pathlib.Path.cwd")
    def test_get_system_context(
        self, mock_cwd, mock_env_get, mock_version, mock_system
    ):
        """Test collecting system context."""
        mock_system.return_value = "Linux"
        mock_version.return_value = "5.15.0"
        mock_env_get.return_value = "/bin/bash"
        mock_cwd.return_value = Path("/home/user/project")

        context = get_system_context()

        assert context.os_name == "Linux"
        assert context.os_version == "5.15.0"
        assert context.shell == "/bin/bash"
        assert context.cwd == Path("/home/user/project")
        assert isinstance(context.python_version, str)

    @patch("os.environ.get")
    def test_get_system_context_no_shell(self, mock_env_get):
        """Test system context when SHELL env var is not set."""
        mock_env_get.return_value = None

        context = get_system_context()

        assert context.shell == "unknown"


class TestGitContext:
    """Tests for get_git_context function."""

    @patch("subprocess.run")
    def test_get_git_context_not_a_repo(self, mock_run):
        """Test git context when not in a git repository."""
        mock_run.return_value = MagicMock(returncode=1)

        result = get_git_context(Path("/tmp"))

        assert result is None

    @patch("subprocess.run")
    def test_get_git_context_success(self, mock_run):
        """Test successfully collecting git context."""
        # Mock git rev-parse --show-toplevel
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/home/user/repo\n"),
            # Mock git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout="main\n"),
            # Mock git log
            MagicMock(
                returncode=0,
                stdout=(
                    "abc123\n"
                    "John Doe\n"
                    "2024-01-01 12:00:00 +0000\n"
                    "Initial commit\n"
                    "---COMMIT-END---\n"
                ),
            ),
            # Mock git show --stat for commit
            MagicMock(returncode=0, stdout="file.py | 10 ++++++++++\n"),
            # Mock git diff HEAD
            MagicMock(returncode=0, stdout="diff --git a/file.py b/file.py\n"),
            # Mock git ls-files --others
            MagicMock(returncode=0, stdout="new_file.py\n"),
        ]

        result = get_git_context(Path("/home/user/repo"))

        assert result is not None
        assert result.branch == "main"
        assert result.repo_root == Path("/home/user/repo")
        assert len(result.recent_commits) == 1
        assert result.recent_commits[0].hash == "abc123"
        assert result.recent_commits[0].author == "John Doe"
        assert result.recent_commits[0].message == "Initial commit"
        assert "file.py" in result.recent_commits[0].diff
        assert "diff --git" in result.uncommitted_changes
        assert "new_file.py" in result.uncommitted_changes

    @patch("subprocess.run")
    def test_get_git_context_subprocess_error(self, mock_run):
        """Test git context when subprocess raises an error."""
        mock_run.side_effect = subprocess.SubprocessError("Error")

        result = get_git_context(Path("/tmp"))

        assert result is None

    @patch("subprocess.run")
    def test_get_git_context_timeout(self, mock_run):
        """Test git context when subprocess times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_git_context(Path("/tmp"))

        assert result is None


class TestBuildContext:
    """Tests for build_context function."""

    @patch("lazarus.core.context.get_system_context")
    @patch("lazarus.core.context.get_git_context")
    def test_build_context_with_git(
        self, mock_git_context, mock_system_context, tmp_path
    ):
        """Test building context with git repository."""
        # Create a test script
        script_path = tmp_path / "test_script.py"
        script_path.write_text("print('Hello, World!')")

        # Mock contexts
        mock_git = GitContext(
            branch="main",
            recent_commits=[],
            uncommitted_changes="",
            repo_root=tmp_path,
        )
        mock_git_context.return_value = mock_git

        mock_system = SystemContext(
            os_name="Linux",
            os_version="5.15.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=tmp_path,
        )
        mock_system_context.return_value = mock_system

        # Create execution result
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0,
        )

        # Create config
        config = LazarusConfig()

        # Build context
        context = build_context(script_path, result, config)

        assert context.script_path == script_path
        assert context.script_content == "print('Hello, World!')"
        assert context.execution_result == result
        assert context.git_context == mock_git
        assert context.system_context == mock_system
        assert context.config == config

    @patch("lazarus.core.context.get_system_context")
    @patch("lazarus.core.context.get_git_context")
    def test_build_context_without_git(
        self, mock_git_context, mock_system_context, tmp_path
    ):
        """Test building context without git repository."""
        # Create a test script
        script_path = tmp_path / "test_script.sh"
        script_path.write_text("#!/bin/bash\necho 'test'")

        # Mock contexts
        mock_git_context.return_value = None

        mock_system = SystemContext(
            os_name="Darwin",
            os_version="21.0.0",
            python_version="3.12.0",
            shell="/bin/zsh",
            cwd=tmp_path,
        )
        mock_system_context.return_value = mock_system

        # Create execution result
        result = ExecutionResult(
            exit_code=127,
            stdout="",
            stderr="Command not found",
            duration=0.1,
        )

        # Create config
        config = LazarusConfig()

        # Build context
        context = build_context(script_path, result, config)

        assert context.script_path == script_path
        assert context.script_content == "#!/bin/bash\necho 'test'"
        assert context.execution_result == result
        assert context.git_context is None
        assert context.system_context == mock_system

    def test_build_context_file_not_found(self):
        """Test building context when script file doesn't exist."""
        script_path = Path("/nonexistent/script.py")
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="",
            duration=0.0,
        )
        config = LazarusConfig()

        with pytest.raises(FileNotFoundError):
            build_context(script_path, result, config)
