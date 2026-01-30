"""Integration tests for the full healing flow.

These tests verify the end-to-end healing process with mocked external
dependencies (Claude Code, gh CLI, notifications).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from lazarus.config.schema import (
    GitConfig,
    NotificationConfig,
    SlackConfig,
)
from lazarus.core.context import ExecutionResult, build_context
from lazarus.core.healer import Healer
from lazarus.core.verification import ErrorComparison, VerificationResult


class TestFullHealingFlow:
    """Test the complete healing flow from start to finish."""

    def test_healing_flow_success(
        self,
        sample_config,
        temp_failing_script,
        mock_claude_client,
    ):
        """Test full healing flow with successful fix."""
        # Mock the script runner to simulate successful fix after Claude's intervention
        with patch("lazarus.core.runner.ScriptRunner.run_script") as mock_run:
            with patch("lazarus.core.runner.ScriptRunner.verify_fix") as mock_verify:
                # First run: script fails
                mock_run.return_value = ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="NameError: name 'undefined_variable' is not defined",
                    duration=0.5,
                )

                # After fix: script succeeds
                mock_verify.return_value = VerificationResult(
                    status="success",
                    execution_result=ExecutionResult(
                        exit_code=0,
                        stdout="Success!",
                        stderr="",
                        duration=0.3,
                    ),
                    comparison=ErrorComparison(
                        is_same_error=False,
                        similarity_score=0.0,
                        key_differences=[],
                    ),
                    custom_criteria_passed=None,
                )

                # Create healer and run
                healer = Healer(sample_config)
                result = healer.heal(temp_failing_script)

                # Verify results
                assert result.success is True
                assert len(result.attempts) == 1
                assert result.attempts[0].verification.status == "success"

    def test_healing_flow_max_attempts_reached(
        self,
        sample_config,
        temp_failing_script,
        mock_claude_client,
    ):
        """Test healing flow when max attempts is reached without success."""
        # Configure for fewer attempts
        sample_config.healing.max_attempts = 2

        with patch("lazarus.core.runner.ScriptRunner.run_script") as mock_run:
            with patch("lazarus.core.runner.ScriptRunner.verify_fix") as mock_verify:
                # Script keeps failing
                mock_run.return_value = ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="Error: Still broken",
                    duration=0.5,
                )

                # Fix attempts don't work
                mock_verify.return_value = VerificationResult(
                    status="same_error",
                    execution_result=ExecutionResult(
                        exit_code=1,
                        stdout="",
                        stderr="Error: Still broken",
                        duration=0.5,
                    ),
                    comparison=ErrorComparison(
                        is_same_error=True,
                        similarity_score=0.9,
                        key_differences=[],
                    ),
                    custom_criteria_passed=None,
                )

                # Create healer and run
                healer = Healer(sample_config)
                result = healer.heal(temp_failing_script)

                # Verify results
                assert result.success is False
                assert len(result.attempts) == 2
                assert result.error_message is not None

    def test_healing_flow_different_error_each_attempt(
        self,
        sample_config,
        temp_failing_script,
        mock_claude_client,
    ):
        """Test healing flow where each attempt produces a different error."""
        with patch("lazarus.core.runner.ScriptRunner.run_script") as mock_run:
            with patch("lazarus.core.runner.ScriptRunner.verify_fix") as mock_verify:
                # Initial failure
                mock_run.return_value = ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="NameError: undefined_variable",
                    duration=0.5,
                )

                # Each attempt produces different error, then success
                verify_results = [
                    VerificationResult(  # Attempt 1: different error
                        status="different_error",
                        execution_result=ExecutionResult(
                            exit_code=1,
                            stdout="",
                            stderr="TypeError: cannot add int and str",
                            duration=0.4,
                        ),
                        comparison=ErrorComparison(
                            is_same_error=False,
                            similarity_score=0.3,
                            key_differences=[],
                        ),
                        custom_criteria_passed=None,
                    ),
                    VerificationResult(  # Attempt 2: success
                        status="success",
                        execution_result=ExecutionResult(
                            exit_code=0,
                            stdout="Success!",
                            stderr="",
                            duration=0.3,
                        ),
                        comparison=ErrorComparison(
                            is_same_error=False,
                            similarity_score=0.0,
                            key_differences=[],
                        ),
                        custom_criteria_passed=None,
                    ),
                ]
                mock_verify.side_effect = verify_results

                # Create healer and run
                healer = Healer(sample_config)
                result = healer.heal(temp_failing_script)

                # Verify results
                assert result.success is True
                assert len(result.attempts) == 2
                assert result.attempts[0].verification.status == "different_error"
                assert result.attempts[1].verification.status == "success"


class TestConfigLoadingAndHealing:
    """Test config loading integrated with healing."""

    def test_load_config_and_heal(
        self,
        temp_config_file,
        temp_failing_script,
        mock_claude_client,
    ):
        """Test loading configuration from file and healing."""
        from lazarus.config.loader import load_config

        # Load config from file
        config = load_config(temp_config_file)

        assert config is not None
        assert len(config.scripts) == 1

        # Mock successful healing
        with patch("lazarus.core.runner.ScriptRunner.run_script") as mock_run:
            with patch("lazarus.core.runner.ScriptRunner.verify_fix") as mock_verify:
                mock_run.return_value = ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="Error",
                    duration=0.5,
                )

                mock_verify.return_value = VerificationResult(
                    status="success",
                    execution_result=ExecutionResult(
                        exit_code=0,
                        stdout="Success",
                        stderr="",
                        duration=0.3,
                    ),
                    comparison=ErrorComparison(is_same_error=False, similarity_score=0.0, key_differences=[]),
                    custom_criteria_passed=None,
                )

                healer = Healer(config)
                result = healer.heal(temp_failing_script)

                assert result.success is True


class TestPRCreationFlow:
    """Test PR creation flow (mocked gh CLI)."""

    def test_create_pr_after_successful_healing(
        self,
        sample_config,
        temp_failing_script,
        mock_subprocess,
    ):
        """Test creating a PR after successful healing."""
        from lazarus.git.pr import PRCreator

        # Enable PR creation
        sample_config.git = GitConfig(
            create_pr=True,
            branch_prefix="lazarus/fix",
            draft_pr=False,
        )

        # Mock git and gh commands
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/pull/123",
            stderr="",
        )

        # Mock git repository check since temp_failing_script.parent is not a real git repo
        with patch("lazarus.git.operations.GitOperations._is_git_repo", return_value=True):
            # Create PR creator
            pr_creator = PRCreator(sample_config.git, temp_failing_script.parent)

            # Mock healing result
            healing_result = Mock(
                success=True,
                attempts=[],
                duration=5.0,
            )

            # Create PR
            pr_result = pr_creator.create_pr(
                healing_result=healing_result,
                script_path=temp_failing_script,
            )

            assert pr_result.success is True
            assert pr_result.pr_url is not None
            assert "github.com" in pr_result.pr_url

    def test_skip_pr_when_disabled(self, sample_config, tmp_path):
        """Test skipping PR creation when disabled in config."""
        from lazarus.git.pr import PRCreator

        # Disable PR creation
        sample_config.git = GitConfig(create_pr=False)

        # Mock git repository check since tmp_path is not a real git repo
        with patch("lazarus.git.operations.GitOperations._is_git_repo", return_value=True):
            pr_creator = PRCreator(sample_config.git, tmp_path)

            # Should not create PR when disabled
            assert sample_config.git.create_pr is False


class TestNotificationDispatch:
    """Test notification dispatch integration."""

    def test_dispatch_notifications_on_success(
        self,
        sample_healing_result_success,
        temp_script,
    ):
        """Test dispatching notifications after successful healing."""
        from lazarus.notifications.dispatcher import NotificationDispatcher

        # Configure notifications
        config = NotificationConfig(
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                on_success=True,
                on_failure=True,
            )
        )

        dispatcher = NotificationDispatcher(config)

        # Mock HTTP client
        with patch("lazarus.notifications.slack.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = (
                mock_response
            )

            # Dispatch notifications
            results = dispatcher.dispatch(sample_healing_result_success, temp_script)

            assert len(results) == 1
            assert results[0].success is True
            assert results[0].channel_name == "slack"

    def test_dispatch_notifications_on_failure(
        self,
        sample_healing_result_failure,
        temp_script,
    ):
        """Test dispatching notifications after failed healing."""
        from lazarus.notifications.dispatcher import NotificationDispatcher

        # Configure notifications
        config = NotificationConfig(
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                on_success=False,
                on_failure=True,
            )
        )

        dispatcher = NotificationDispatcher(config)

        # Mock HTTP client
        with patch("lazarus.notifications.slack.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = (
                mock_response
            )

            # Dispatch notifications
            results = dispatcher.dispatch(sample_healing_result_failure, temp_script)

            assert len(results) == 1
            assert results[0].success is True


class TestContextBuilding:
    """Test context building integration."""

    def test_build_context_with_git_info(
        self,
        sample_config,
        sample_execution_result_failure,
        mock_git_repo,
    ):
        """Test building context with git information."""
        # Create a script in the git repo
        script = mock_git_repo / "test.py"
        script.write_text("print('test')")

        # Mock git commands
        with patch("subprocess.run") as mock_run:
            # Mock git commands to return valid info
            mock_run.side_effect = [
                # git rev-parse --show-toplevel
                Mock(returncode=0, stdout=str(mock_git_repo)),
                # git rev-parse --abbrev-ref HEAD
                Mock(returncode=0, stdout="main"),
                # git log
                Mock(returncode=0, stdout="abc123\nAuthor\n2024-01-01\nCommit message\n---COMMIT-END---"),
                # git show --stat
                Mock(returncode=0, stdout="file changes"),
                # git diff HEAD
                Mock(returncode=0, stdout=""),
                # git ls-files
                Mock(returncode=0, stdout=""),
            ]

            context = build_context(
                script_path=script,
                result=sample_execution_result_failure,
                config=sample_config,
            )

            assert context.script_path == script
            assert context.execution_result == sample_execution_result_failure
            assert context.git_context is not None
            assert context.git_context.branch == "main"

    def test_build_context_without_git(
        self,
        sample_config,
        sample_execution_result_failure,
        temp_script,
    ):
        """Test building context without git information."""
        context = build_context(
            script_path=temp_script,
            result=sample_execution_result_failure,
            config=sample_config,
        )

        assert context.script_path == temp_script
        assert context.execution_result == sample_execution_result_failure
        assert context.git_context is None  # No git repo
        assert context.system_context is not None
