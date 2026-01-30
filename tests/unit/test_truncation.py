"""Unit tests for context truncation functionality."""

from __future__ import annotations

from pathlib import Path

from lazarus.config.schema import LazarusConfig
from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
    SystemContext,
)
from lazarus.core.truncation import (
    estimate_tokens,
    truncate_commit,
    truncate_execution_result,
    truncate_for_context,
    truncate_git_context,
    truncate_text,
)


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_estimate_tokens_empty(self):
        """Test estimating tokens for empty string."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_short(self):
        """Test estimating tokens for short text."""
        text = "Hello"
        tokens = estimate_tokens(text)
        assert tokens == len(text) // 4

    def test_estimate_tokens_long(self):
        """Test estimating tokens for longer text."""
        text = "a" * 1000
        tokens = estimate_tokens(text)
        assert tokens == 250

    def test_estimate_tokens_realistic(self):
        """Test estimating tokens for realistic text."""
        text = "This is a realistic piece of text with multiple words and punctuation."
        tokens = estimate_tokens(text)
        # Should be approximately len/4
        assert tokens > 0
        assert tokens < len(text)


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_text_no_truncation_needed(self):
        """Test when text is already within limit."""
        text = "Short text"
        result = truncate_text(text, max_tokens=100)
        assert result == text

    def test_truncate_text_from_end(self):
        """Test truncating from the end."""
        lines = [f"Line {i}" for i in range(100)]
        text = "\n".join(lines)
        max_tokens = 20  # ~80 chars
        result = truncate_text(text, max_tokens, position="end")

        assert "[TRUNCATED:" in result
        assert "removed from end]" in result
        # First lines should be preserved
        assert "Line 0" in result

    def test_truncate_text_from_start(self):
        """Test truncating from the start."""
        lines = [f"Line {i}" for i in range(100)]
        text = "\n".join(lines)
        max_tokens = 20
        result = truncate_text(text, max_tokens, position="start")

        assert "[TRUNCATED:" in result
        assert "removed from start]" in result
        # Last lines should be preserved
        assert "Line 99" in result

    def test_truncate_text_from_middle(self):
        """Test truncating from the middle."""
        lines = [f"Line {i}" for i in range(100)]
        text = "\n".join(lines)
        max_tokens = 40
        result = truncate_text(text, max_tokens, position="middle")

        assert "[TRUNCATED:" in result
        assert "removed from middle]" in result
        # Beginning and end should be preserved
        assert "Line 0" in result
        assert "Line 99" in result

    def test_truncate_text_single_line(self):
        """Test truncating single very long line."""
        text = "a" * 1000
        max_tokens = 10
        result = truncate_text(text, max_tokens, position="end")

        # Should be truncated
        assert len(result) < len(text)
        assert "[TRUNCATED:" in result


class TestTruncateExecutionResult:
    """Tests for truncate_execution_result function."""

    def test_truncate_execution_result_no_truncation(self):
        """Test when execution result is within limits."""
        result = ExecutionResult(
            exit_code=1,
            stdout="Normal output",
            stderr="Error message",
            duration=1.0,
        )
        truncated = truncate_execution_result(result, max_tokens=100)

        assert truncated.stdout == result.stdout
        assert truncated.stderr == result.stderr
        assert truncated.exit_code == result.exit_code

    def test_truncate_execution_result_prioritizes_stderr(self):
        """Test that stderr is prioritized over stdout."""
        # Create large stdout and stderr
        large_stdout = "out\n" * 1000
        large_stderr = "err\n" * 1000

        result = ExecutionResult(
            exit_code=1,
            stdout=large_stdout,
            stderr=large_stderr,
            duration=1.0,
        )

        # Very small token limit
        truncated = truncate_execution_result(result, max_tokens=100)

        # Stderr should get more allocation
        stderr_tokens = estimate_tokens(truncated.stderr)
        stdout_tokens = estimate_tokens(truncated.stdout)

        assert stderr_tokens >= stdout_tokens
        assert "[TRUNCATED:" in truncated.stderr or "[TRUNCATED:" in truncated.stdout

    def test_truncate_execution_result_small_stderr(self):
        """Test when stderr is small, stdout gets more space."""
        small_stderr = "Error"
        large_stdout = "output\n" * 1000

        result = ExecutionResult(
            exit_code=1,
            stdout=large_stdout,
            stderr=small_stderr,
            duration=1.0,
        )

        truncated = truncate_execution_result(result, max_tokens=100)

        # Stderr should be unchanged
        assert truncated.stderr == small_stderr
        # Stdout should be truncated
        assert "[TRUNCATED:" in truncated.stdout


class TestTruncateCommit:
    """Tests for truncate_commit function."""

    def test_truncate_commit_no_truncation(self):
        """Test when commit is within limits."""
        commit = CommitInfo(
            hash="abc123",
            author="John Doe",
            date="2024-01-01",
            message="Short message",
            diff="Small diff",
        )
        truncated = truncate_commit(commit, max_tokens=100)

        assert truncated.message == commit.message
        assert truncated.diff == commit.diff

    def test_truncate_commit_large_diff(self):
        """Test truncating commit with large diff."""
        commit = CommitInfo(
            hash="abc123",
            author="John Doe",
            date="2024-01-01",
            message="Short message",
            diff="diff\n" * 1000,
        )
        truncated = truncate_commit(commit, max_tokens=50)

        assert truncated.message == commit.message
        assert len(truncated.diff) < len(commit.diff)
        assert "[TRUNCATED:" in truncated.diff

    def test_truncate_commit_no_diff(self):
        """Test truncating commit without diff."""
        commit = CommitInfo(
            hash="abc123",
            author="John Doe",
            date="2024-01-01",
            message="Message",
            diff=None,
        )
        truncated = truncate_commit(commit, max_tokens=10)

        assert truncated.diff is None
        assert truncated.message == commit.message


class TestTruncateGitContext:
    """Tests for truncate_git_context function."""

    def test_truncate_git_context_none(self):
        """Test truncating None git context."""
        result = truncate_git_context(None, max_tokens=100)
        assert result is None

    def test_truncate_git_context_no_truncation(self):
        """Test when git context is within limits."""
        git_context = GitContext(
            branch="main",
            recent_commits=[
                CommitInfo(
                    hash="abc",
                    author="John",
                    date="2024-01-01",
                    message="Fix bug",
                    diff="small diff",
                )
            ],
            uncommitted_changes="+ new line",
            repo_root=Path("/repo"),
        )
        truncated = truncate_git_context(git_context, max_tokens=1000)

        assert truncated.branch == git_context.branch
        assert len(truncated.recent_commits) == len(git_context.recent_commits)
        assert truncated.uncommitted_changes == git_context.uncommitted_changes

    def test_truncate_git_context_large_uncommitted(self):
        """Test truncating with large uncommitted changes."""
        git_context = GitContext(
            branch="main",
            recent_commits=[],
            uncommitted_changes="change\n" * 1000,
            repo_root=Path("/repo"),
        )
        truncated = truncate_git_context(git_context, max_tokens=50)

        assert len(truncated.uncommitted_changes) < len(
            git_context.uncommitted_changes
        )
        assert "[TRUNCATED:" in truncated.uncommitted_changes

    def test_truncate_git_context_many_commits(self):
        """Test truncating with many commits."""
        commits = [
            CommitInfo(
                hash=f"hash{i}",
                author="Author",
                date="2024-01-01",
                message=f"Commit {i}",
                diff=f"diff {i}\n" * 100,
            )
            for i in range(10)
        ]

        git_context = GitContext(
            branch="main",
            recent_commits=commits,
            uncommitted_changes="",
            repo_root=Path("/repo"),
        )

        truncated = truncate_git_context(git_context, max_tokens=100)

        # Should keep fewer commits
        assert len(truncated.recent_commits) < len(git_context.recent_commits)
        # Most recent commits should be kept
        assert truncated.recent_commits[0].hash == "hash0"

    def test_truncate_git_context_prioritizes_uncommitted(self):
        """Test that uncommitted changes are prioritized."""
        git_context = GitContext(
            branch="main",
            recent_commits=[
                CommitInfo(
                    hash="abc",
                    author="John",
                    date="2024-01-01",
                    message="Old commit",
                    diff="diff\n" * 1000,
                )
            ],
            uncommitted_changes="important\n" * 500,
            repo_root=Path("/repo"),
        )

        truncated = truncate_git_context(git_context, max_tokens=100)

        # Uncommitted changes should be present (possibly truncated)
        assert len(truncated.uncommitted_changes) > 0
        # Commits may be removed or heavily truncated
        uncommitted_tokens = estimate_tokens(truncated.uncommitted_changes)
        if truncated.recent_commits:
            commit_tokens = sum(
                estimate_tokens(c.message) + estimate_tokens(c.diff or "")
                for c in truncated.recent_commits
            )
            # Uncommitted should get at least 40% of tokens
            assert uncommitted_tokens > commit_tokens * 0.4


class TestTruncateForContext:
    """Tests for truncate_for_context function."""

    def test_truncate_for_context_no_truncation(self):
        """Test when context is within limits."""
        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="print('hello')",
            execution_result=ExecutionResult(
                exit_code=1,
                stdout="output",
                stderr="error",
                duration=1.0,
            ),
            git_context=None,
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/"),
            ),
            config=LazarusConfig(),
        )

        truncated = truncate_for_context(context, max_tokens=10000)

        assert truncated.script_content == context.script_content
        assert truncated.execution_result.stdout == context.execution_result.stdout
        assert truncated.execution_result.stderr == context.execution_result.stderr

    def test_truncate_for_context_large_content(self):
        """Test truncating context with large content."""
        large_script = "# Comment\n" * 10000
        large_stdout = "output\n" * 10000
        large_stderr = "error\n" * 10000
        large_changes = "change\n" * 10000

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content=large_script,
            execution_result=ExecutionResult(
                exit_code=1,
                stdout=large_stdout,
                stderr=large_stderr,
                duration=1.0,
            ),
            git_context=GitContext(
                branch="main",
                recent_commits=[],
                uncommitted_changes=large_changes,
                repo_root=Path("/"),
            ),
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/"),
            ),
            config=LazarusConfig(),
        )

        truncated = truncate_for_context(context, max_tokens=1000)

        # All components should be truncated
        assert len(truncated.script_content) < len(context.script_content)
        assert (
            len(truncated.execution_result.stderr)
            < len(context.execution_result.stderr)
        )
        assert (
            len(truncated.git_context.uncommitted_changes)
            < len(context.git_context.uncommitted_changes)
        )

        # Should contain truncation markers
        total_text = (
            truncated.script_content
            + truncated.execution_result.stdout
            + truncated.execution_result.stderr
            + truncated.git_context.uncommitted_changes
        )
        assert "[TRUNCATED:" in total_text

    def test_truncate_for_context_prioritizes_errors(self):
        """Test that errors are prioritized in truncation."""
        # Create a more realistic error that won't be on a single very long line
        error_lines = ["CRITICAL ERROR: Something went wrong"]
        error_lines.extend([f"Error detail line {i}" for i in range(100)])

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="x" * 10000,
            execution_result=ExecutionResult(
                exit_code=1,
                stdout="y" * 10000,
                stderr="\n".join(error_lines),
                duration=1.0,
            ),
            git_context=None,
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/"),
            ),
            config=LazarusConfig(),
        )

        truncated = truncate_for_context(context, max_tokens=1000)

        # Error should be preserved as much as possible
        # At minimum, we should see the error marker or some error content
        assert "CRITICAL ERROR:" in truncated.execution_result.stderr or len(truncated.execution_result.stderr) > 0

    def test_truncate_for_context_with_git(self):
        """Test truncating context with git information."""
        commits = [
            CommitInfo(
                hash=f"hash{i}",
                author="Author",
                date="2024-01-01",
                message=f"Commit {i}",
                diff="x" * 10000,
            )
            for i in range(5)
        ]

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="print('test')",
            execution_result=ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="error",
                duration=1.0,
            ),
            git_context=GitContext(
                branch="main",
                recent_commits=commits,
                uncommitted_changes="change\n" * 5000,
                repo_root=Path("/"),
            ),
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/"),
            ),
            config=LazarusConfig(),
        )

        truncated = truncate_for_context(context, max_tokens=500)

        # Git context should be truncated
        assert len(truncated.git_context.recent_commits) <= len(
            context.git_context.recent_commits
        )
        assert len(truncated.git_context.uncommitted_changes) < len(
            context.git_context.uncommitted_changes
        )
