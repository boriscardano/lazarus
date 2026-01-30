"""Unit tests for secrets redaction functionality."""

from __future__ import annotations

from pathlib import Path

from lazarus.config.schema import LazarusConfig, SecurityConfig
from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
    SystemContext,
)
from lazarus.security.redactor import (
    Redactor,
    filter_environment_variables,
    redact_commit_info,
    redact_context,
    redact_execution_result,
    redact_git_context,
    redact_system_context,
)


class TestRedactor:
    """Tests for Redactor class."""

    def test_redactor_initialization(self):
        """Test creating a Redactor with patterns."""
        patterns = [
            ("api_key", r"api_key=[a-z0-9]+"),
            ("password", r"password=[^\s]+"),
        ]
        redactor = Redactor(patterns)

        assert len(redactor.patterns) == 2

    def test_redactor_from_config(self):
        """Test creating Redactor from config."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        # Should have patterns from default security config
        assert len(redactor.patterns) > 0

    def test_redactor_from_config_with_additional_patterns(self):
        """Test creating Redactor with additional patterns."""
        config = LazarusConfig(
            security=SecurityConfig(
                additional_patterns=[r"custom_secret=[a-z0-9]+"]
            )
        )
        redactor = Redactor.from_config(config)

        # Should have default + additional patterns
        assert len(redactor.patterns) > len(
            LazarusConfig().security.redact_patterns
        )

    def test_redact_api_key(self):
        """Test redacting API key."""
        patterns = [("api_key", r"(?i)api[_-]?key[\s=:]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?")]
        redactor = Redactor(patterns)

        text = "Using API_KEY=test_key_FAKE1234567890abcdef for authentication"
        redacted = redactor.redact(text)

        assert "test_key_FAKE1234567890abcdef" not in redacted
        assert "[REDACTED:api_key]" in redacted

    def test_redact_password(self):
        """Test redacting password."""
        patterns = [("password", r"(?i)(password|passwd|pwd)[\s=:]+['\"]?([^\s'\"]{8,})['\"]?")]
        redactor = Redactor(patterns)

        text = "Database password=MySecretPass123 is configured"
        redacted = redactor.redact(text)

        assert "MySecretPass123" not in redacted
        assert "[REDACTED:password]" in redacted

    def test_redact_token(self):
        """Test redacting bearer token."""
        patterns = [("bearer", r"(?i)(bearer\s+[a-zA-Z0-9_\-\.]+)")]
        redactor = Redactor(patterns)

        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        redacted = redactor.redact(text)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "[REDACTED:bearer]" in redacted

    def test_redact_aws_credentials(self):
        """Test redacting AWS credentials."""
        patterns = [
            ("aws_access_key", r"(?i)(aws[_-]?access[_-]?key[_-]?id)[\s=:]+['\"]?([A-Z0-9]{20})['\"]?"),
            ("aws_secret_key", r"(?i)(aws[_-]?secret[_-]?access[_-]?key)[\s=:]+['\"]?([a-zA-Z0-9/+=]{40})['\"]?"),
        ]
        redactor = Redactor(patterns)

        text = """
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        """
        redacted = redactor.redact(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted
        assert "[REDACTED:aws_access_key]" in redacted
        assert "[REDACTED:aws_secret_key]" in redacted

    def test_redact_multiple_secrets(self):
        """Test redacting multiple different secrets."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        text = """
        export API_KEY=test_key_FAKE1234567890abcdefgh
        export PASSWORD=MyVerySecretPassword123
        export TOKEN=ghx_FAKE1234567890abcdefghijklmnopqrst
        """
        redacted = redactor.redact(text)

        assert "test_key_FAKE1234567890abcdefgh" not in redacted
        assert "MyVerySecretPassword123" not in redacted
        assert "ghx_FAKE1234567890abcdefghijklmnopqrst" not in redacted
        assert "[REDACTED:" in redacted

    def test_redact_no_secrets(self):
        """Test redacting text with no secrets."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        text = "This is just normal text with no secrets"
        redacted = redactor.redact(text)

        assert redacted == text

    def test_redact_dict(self):
        """Test redacting dictionary values."""
        patterns = [("api_key", r"api_key_[a-z0-9]+")]
        redactor = Redactor(patterns)

        data = {
            "user": "john",
            "key": "api_key_secret123",
            "config": "Some text with api_key_another456",
        }
        redacted = redactor.redact_dict(data)

        assert redacted["user"] == "john"
        assert "api_key_secret123" not in redacted["key"]
        assert "api_key_another456" not in redacted["config"]
        assert "[REDACTED:api_key]" in redacted["key"]


class TestRedactExecutionResult:
    """Tests for redact_execution_result function."""

    def test_redact_execution_result(self):
        """Test redacting execution result."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        result = ExecutionResult(
            exit_code=1,
            stdout="Connection successful with token=abc123def456ghi789jkl012mno345",
            stderr="Error: Invalid API_KEY test_key_FAKE1234567890abcdefklmn",
            duration=1.5,
        )

        redacted = redact_execution_result(result, redactor)

        assert "abc123def456ghi789jkl012mno345" not in redacted.stdout
        assert "test_key_FAKE1234567890abcdefklmn" not in redacted.stderr
        assert "[REDACTED:" in redacted.stdout
        assert "[REDACTED:" in redacted.stderr
        assert redacted.exit_code == result.exit_code
        assert redacted.duration == result.duration


class TestRedactCommitInfo:
    """Tests for redact_commit_info function."""

    def test_redact_commit_info(self):
        """Test redacting commit info."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        commit = CommitInfo(
            hash="abc123",
            author="John Doe",
            date="2024-01-01",
            message="Add API_KEY test_key_FAKE1234567890abcdefgh",
            diff="+ password=VerySecretPassword123\n- old code",
        )

        redacted = redact_commit_info(commit, redactor)

        assert "test_key_FAKE1234567890abcdefgh" not in redacted.message
        assert "VerySecretPassword123" not in redacted.diff
        assert "[REDACTED:" in redacted.message
        assert "[REDACTED:" in redacted.diff
        assert redacted.hash == commit.hash
        assert redacted.author == commit.author

    def test_redact_commit_info_no_diff(self):
        """Test redacting commit info without diff."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        commit = CommitInfo(
            hash="def456",
            author="Jane Doe",
            date="2024-01-02",
            message="Fix bug",
            diff=None,
        )

        redacted = redact_commit_info(commit, redactor)

        assert redacted.diff is None
        assert redacted.message == commit.message


class TestRedactGitContext:
    """Tests for redact_git_context function."""

    def test_redact_git_context(self):
        """Test redacting git context."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        git_context = GitContext(
            branch="main",
            recent_commits=[
                CommitInfo(
                    hash="abc",
                    author="John",
                    date="2024-01-01",
                    message="Add secret token=ghx_FAKE1234567890abcdefghijklmnopqrst",
                    diff="+ new feature",
                ),
            ],
            uncommitted_changes="+ export API_KEY=test_key_FAKE1234567890abcdefklmn",
            repo_root=Path("/repo"),
        )

        redacted = redact_git_context(git_context, redactor)

        assert "ghx_FAKE1234567890abcdefghijklmnopqrst" not in redacted.recent_commits[0].message
        assert "test_key_FAKE1234567890abcdefklmn" not in redacted.uncommitted_changes
        assert "[REDACTED:" in redacted.recent_commits[0].message
        assert "[REDACTED:" in redacted.uncommitted_changes

    def test_redact_git_context_none(self):
        """Test redacting None git context."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        redacted = redact_git_context(None, redactor)

        assert redacted is None


class TestRedactSystemContext:
    """Tests for redact_system_context function."""

    def test_redact_system_context(self):
        """Test redacting system context."""
        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        system_context = SystemContext(
            os_name="Linux",
            os_version="5.15.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/home/user"),
        )

        redacted = redact_system_context(system_context, redactor)

        # System context typically doesn't have secrets, but we still process it
        assert redacted.os_name == system_context.os_name
        assert redacted.os_version == system_context.os_version


class TestRedactContext:
    """Tests for redact_context function."""

    def test_redact_context_full(self):
        """Test redacting complete healing context."""
        config = LazarusConfig()

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="API_KEY = 'test_key_FAKE1234567890abcdefklmn'",
            execution_result=ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="Error: token ghx_FAKE1234567890abcdefghijklmnopqrst invalid",
                duration=1.0,
            ),
            git_context=GitContext(
                branch="main",
                recent_commits=[],
                uncommitted_changes="+ password=SecretPass123456",
                repo_root=Path("/repo"),
            ),
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/repo"),
            ),
            config=config,
        )

        redacted = redact_context(context)

        assert "test_key_FAKE1234567890abcdefklmn" not in redacted.script_content
        assert "ghx_FAKE1234567890abcdefghijklmnopqrst" not in redacted.execution_result.stderr
        assert "SecretPass123456" not in redacted.git_context.uncommitted_changes
        assert "[REDACTED:" in redacted.script_content
        assert "[REDACTED:" in redacted.execution_result.stderr


class TestFilterEnvironmentVariables:
    """Tests for filter_environment_variables function."""

    def test_filter_safe_variables(self):
        """Test filtering to keep only safe variables."""
        env_vars = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/user",
            "API_KEY": "secret",
            "PASSWORD": "secret123",
            "USER": "john",
        }
        safe_vars = ["PATH", "HOME", "USER"]

        filtered = filter_environment_variables(env_vars, safe_vars)

        assert "PATH" in filtered
        assert "HOME" in filtered
        assert "USER" in filtered
        assert "API_KEY" not in filtered
        assert "PASSWORD" not in filtered

    def test_filter_empty_safe_list(self):
        """Test filtering with empty safe list."""
        env_vars = {
            "PATH": "/usr/bin",
            "API_KEY": "secret",
        }
        safe_vars = []

        filtered = filter_environment_variables(env_vars, safe_vars)

        assert len(filtered) == 0

    def test_filter_all_unsafe(self):
        """Test when all variables are unsafe."""
        env_vars = {
            "API_KEY": "secret",
            "PASSWORD": "secret123",
        }
        safe_vars = ["PATH", "HOME"]

        filtered = filter_environment_variables(env_vars, safe_vars)

        assert len(filtered) == 0


class TestRedactPreviousAttempt:
    """Tests for redact_previous_attempt function."""

    def test_redact_previous_attempt(self):
        """Test redacting previous attempt with secrets in error_after."""
        from lazarus.core.context import PreviousAttempt
        from lazarus.security.redactor import redact_previous_attempt

        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        attempt = PreviousAttempt(
            attempt_number=1,
            claude_response_summary="Tried to fix authentication with API_KEY test_key_FAKE1234567890abcdefklmn",
            changes_made=["auth.py", "config.py"],
            error_after="Error: Invalid token ghx_FAKE1234567890abcdefghijklmnopqrst in authentication",
        )

        redacted = redact_previous_attempt(attempt, redactor)

        assert "test_key_FAKE1234567890abcdefklmn" not in redacted.claude_response_summary
        assert "ghx_FAKE1234567890abcdefghijklmnopqrst" not in redacted.error_after
        assert "[REDACTED:" in redacted.claude_response_summary
        assert "[REDACTED:" in redacted.error_after
        assert redacted.attempt_number == attempt.attempt_number
        assert redacted.changes_made == attempt.changes_made

    def test_redact_previous_attempt_no_secrets(self):
        """Test redacting previous attempt with no secrets."""
        from lazarus.core.context import PreviousAttempt
        from lazarus.security.redactor import redact_previous_attempt

        config = LazarusConfig()
        redactor = Redactor.from_config(config)

        attempt = PreviousAttempt(
            attempt_number=2,
            claude_response_summary="Fixed syntax error in main function",
            changes_made=["main.py"],
            error_after="SyntaxError: invalid syntax on line 42",
        )

        redacted = redact_previous_attempt(attempt, redactor)

        # No secrets, so should be unchanged
        assert redacted.claude_response_summary == attempt.claude_response_summary
        assert redacted.error_after == attempt.error_after


class TestRedactContextWithPreviousAttempts:
    """Tests for redact_context function with previous attempts."""

    def test_redact_context_with_previous_attempts(self):
        """Test redacting context with previous attempts containing secrets."""
        from lazarus.core.context import PreviousAttempt

        config = LazarusConfig()

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="import os",
            execution_result=ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="Current error",
                duration=1.0,
            ),
            git_context=None,
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/home"),
            ),
            config=config,
            previous_attempts=[
                PreviousAttempt(
                    attempt_number=1,
                    claude_response_summary="Added API_KEY test_key_FAKE1234567890abcdefklmn",
                    changes_made=["config.py"],
                    error_after="Error: token ghx_FAKE1234567890abcdefghijklmnopqrst is invalid",
                ),
                PreviousAttempt(
                    attempt_number=2,
                    claude_response_summary="Changed password SecretPass123456",
                    changes_made=["auth.py"],
                    error_after="Connection failed with password=AnotherSecret999",
                ),
            ],
        )

        redacted = redact_context(context)

        # Verify previous attempts are redacted
        assert len(redacted.previous_attempts) == 2
        
        # First attempt
        assert "test_key_FAKE1234567890abcdefklmn" not in redacted.previous_attempts[0].claude_response_summary
        assert "ghx_FAKE1234567890abcdefghijklmnopqrst" not in redacted.previous_attempts[0].error_after
        assert "[REDACTED:" in redacted.previous_attempts[0].claude_response_summary
        assert "[REDACTED:" in redacted.previous_attempts[0].error_after
        
        # Second attempt
        assert "SecretPass123456" not in redacted.previous_attempts[1].claude_response_summary
        assert "AnotherSecret999" not in redacted.previous_attempts[1].error_after
        assert "[REDACTED:" in redacted.previous_attempts[1].claude_response_summary
        assert "[REDACTED:" in redacted.previous_attempts[1].error_after

    def test_redact_context_empty_previous_attempts(self):
        """Test redacting context with empty previous attempts list."""
        config = LazarusConfig()

        context = HealingContext(
            script_path=Path("/script.py"),
            script_content="print('hello')",
            execution_result=ExecutionResult(
                exit_code=0,
                stdout="hello",
                stderr="",
                duration=0.1,
            ),
            git_context=None,
            system_context=SystemContext(
                os_name="Linux",
                os_version="5.15.0",
                python_version="3.11.0",
                shell="/bin/bash",
                cwd=Path("/home"),
            ),
            config=config,
            previous_attempts=[],
        )

        redacted = redact_context(context)

        assert len(redacted.previous_attempts) == 0
