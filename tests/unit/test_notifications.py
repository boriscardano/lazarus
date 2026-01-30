"""Unit tests for notification system.

Tests notification channels and dispatcher functionality.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lazarus.config.schema import (
    DiscordConfig,
    EmailConfig,
    GitHubIssuesConfig,
    NotificationConfig,
    SlackConfig,
    WebhookConfig,
)
from lazarus.core.context import ExecutionResult
from lazarus.core.healer import HealingResult
from lazarus.notifications import (
    DiscordNotifier,
    EmailNotifier,
    GitHubIssueNotifier,
    NotificationDispatcher,
    SlackNotifier,
    WebhookNotifier,
)


@pytest.fixture
def mock_execution_result() -> ExecutionResult:
    """Create a mock execution result."""
    return ExecutionResult(
        exit_code=1,
        stdout="Test output",
        stderr="Error: test failed",
        duration=1.5,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def mock_healing_result(mock_execution_result: ExecutionResult) -> HealingResult:
    """Create a mock healing result."""
    return HealingResult(
        success=False,
        attempts=[],
        final_execution=mock_execution_result,
        pr_url="https://github.com/test/repo/pull/123",
        duration=5.0,
        error_message="Script failed with exit code 1",
    )


@pytest.fixture
def mock_script_path() -> Path:
    """Create a mock script path."""
    return Path("/test/script.py")


class TestSlackNotifier:
    """Tests for Slack notification channel."""

    def test_slack_notifier_init(self):
        """Test Slack notifier initialization."""
        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            on_success=True,
            on_failure=True,
        )
        notifier = SlackNotifier(config)

        assert notifier.name == "slack"
        assert notifier.config == config

    @patch("lazarus.notifications.slack.httpx.Client")
    def test_send_success_notification(
        self,
        mock_client: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test sending successful healing notification."""
        # Make the result successful
        mock_healing_result.success = True

        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            on_success=True,
            on_failure=True,
        )
        notifier = SlackNotifier(config)

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True
        mock_client.return_value.__enter__.return_value.post.assert_called_once()

    @patch("lazarus.notifications.slack.httpx.Client")
    def test_send_failure_notification(
        self,
        mock_client: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test sending failed healing notification."""
        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            on_success=True,
            on_failure=True,
        )
        notifier = SlackNotifier(config)

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True

    def test_skip_on_success_when_disabled(
        self,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test skipping notification for success when disabled."""
        mock_healing_result.success = True

        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            on_success=False,  # Disabled
            on_failure=True,
        )
        notifier = SlackNotifier(config)

        result = notifier.send(mock_healing_result, mock_script_path)

        # Should return True (skipped, not failed)
        assert result is True


class TestDiscordNotifier:
    """Tests for Discord notification channel."""

    def test_discord_notifier_init(self):
        """Test Discord notifier initialization."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/test",
            on_success=True,
            on_failure=True,
        )
        notifier = DiscordNotifier(config)

        assert notifier.name == "discord"
        assert notifier.config == config

    @patch("lazarus.notifications.discord.httpx.Client")
    def test_send_notification(
        self,
        mock_client: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test sending Discord notification."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/test",
            on_success=True,
            on_failure=True,
        )
        notifier = DiscordNotifier(config)

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True


class TestEmailNotifier:
    """Tests for Email notification channel."""

    def test_email_notifier_init(self):
        """Test Email notifier initialization."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            use_tls=True,
        )
        notifier = EmailNotifier(config)

        assert notifier.name == "email"
        assert notifier.config == config

    @patch("lazarus.notifications.email.smtplib.SMTP")
    def test_send_notification(
        self,
        mock_smtp: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test sending email notification."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            username="user",
            password="pass",
            use_tls=True,
        )
        notifier = EmailNotifier(config)

        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


class TestGitHubIssueNotifier:
    """Tests for GitHub Issues notification channel."""

    def test_github_issue_notifier_init(self):
        """Test GitHub Issue notifier initialization."""
        config = GitHubIssuesConfig(
            repo="owner/repo",
            labels=["bug", "auto-heal"],
            on_failure=True,
        )
        notifier = GitHubIssueNotifier(config)

        assert notifier.name == "github_issues"
        assert notifier.config == config

    def test_skip_on_success(
        self,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test skipping issue creation for successful healing."""
        mock_healing_result.success = True

        config = GitHubIssuesConfig(
            repo="owner/repo",
            labels=["bug"],
        )
        notifier = GitHubIssueNotifier(config)

        result = notifier.send(mock_healing_result, mock_script_path)

        # Should skip (return True)
        assert result is True

    @patch("lazarus.notifications.github_issues.subprocess.run")
    def test_send_notification(
        self,
        mock_run: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test creating GitHub issue."""
        config = GitHubIssuesConfig(
            repo="owner/repo",
            labels=["bug"],
            on_failure=True,
        )
        notifier = GitHubIssueNotifier(config)

        # Mock gh auth status check (available)
        auth_result = Mock()
        auth_result.returncode = 0

        # Mock gh issue create (success)
        create_result = Mock()
        create_result.returncode = 0
        create_result.stdout = "https://github.com/owner/repo/issues/123"

        mock_run.side_effect = [auth_result, create_result]

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True
        assert mock_run.call_count == 2


class TestWebhookNotifier:
    """Tests for Webhook notification channel."""

    def test_webhook_notifier_init(self):
        """Test Webhook notifier initialization."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            method="POST",
            headers={"Authorization": "Bearer token"},
        )
        notifier = WebhookNotifier(config)

        assert notifier.name == "webhook"
        assert notifier.config == config

    @patch("lazarus.notifications.webhook.httpx.Client")
    def test_send_notification_post(
        self,
        mock_client: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test sending webhook notification with POST."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            method="POST",
        )
        notifier = WebhookNotifier(config)

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier.send(mock_healing_result, mock_script_path)

        assert result is True
        mock_client.return_value.__enter__.return_value.post.assert_called_once()


class TestNotificationDispatcher:
    """Tests for notification dispatcher."""

    def test_dispatcher_init_no_channels(self):
        """Test dispatcher initialization with no channels."""
        config = NotificationConfig()
        dispatcher = NotificationDispatcher(config)

        assert dispatcher.get_channel_count() == 0
        assert dispatcher.get_channel_names() == []

    def test_dispatcher_init_with_slack(self):
        """Test dispatcher initialization with Slack."""
        config = NotificationConfig(
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
            )
        )
        dispatcher = NotificationDispatcher(config)

        assert dispatcher.get_channel_count() == 1
        assert "slack" in dispatcher.get_channel_names()

    def test_dispatcher_init_all_channels(self):
        """Test dispatcher initialization with all channels."""
        config = NotificationConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
            discord=DiscordConfig(webhook_url="https://discord.com/api/webhooks/test"),
            email=EmailConfig(
                smtp_host="smtp.example.com",
                from_addr="sender@example.com",
                to_addrs=["recipient@example.com"],
            ),
            github_issues=GitHubIssuesConfig(repo="owner/repo"),
            webhook=WebhookConfig(url="https://example.com/webhook"),
        )
        dispatcher = NotificationDispatcher(config)

        assert dispatcher.get_channel_count() == 5
        assert set(dispatcher.get_channel_names()) == {
            "slack", "discord", "email", "github_issues", "webhook"
        }

    @patch("lazarus.notifications.slack.httpx.Client")
    @patch("lazarus.notifications.discord.httpx.Client")
    def test_dispatch_to_multiple_channels(
        self,
        mock_discord_client: Mock,
        mock_slack_client: Mock,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test dispatching to multiple channels."""
        config = NotificationConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
            discord=DiscordConfig(webhook_url="https://discord.com/api/webhooks/test"),
        )
        dispatcher = NotificationDispatcher(config)

        # Mock successful HTTP responses
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_slack_client.return_value.__enter__.return_value.post.return_value = mock_response
        mock_discord_client.return_value.__enter__.return_value.post.return_value = mock_response

        results = dispatcher.dispatch(mock_healing_result, mock_script_path)

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_dispatch_continues_on_failure(
        self,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test dispatcher continues even if one channel fails."""
        config = NotificationConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
            discord=DiscordConfig(webhook_url="https://discord.com/api/webhooks/test"),
        )
        dispatcher = NotificationDispatcher(config)

        # Mock one channel to fail, one to succeed
        with patch.object(dispatcher.channels[0], "send", return_value=False):
            with patch.object(dispatcher.channels[1], "send", return_value=True):
                results = dispatcher.dispatch(mock_healing_result, mock_script_path)

        assert len(results) == 2
        assert not results[0].success
        assert results[1].success

    def test_rate_limiting(
        self,
        mock_healing_result: HealingResult,
        mock_script_path: Path,
    ):
        """Test rate limiting."""
        config = NotificationConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
        )
        # Set very restrictive rate limit
        dispatcher = NotificationDispatcher(config, rate_limit_window=60, rate_limit_max=1)

        # Mock successful sends
        with patch.object(dispatcher.channels[0], "send", return_value=True):
            # First dispatch should succeed
            results1 = dispatcher.dispatch(mock_healing_result, mock_script_path)
            assert len(results1) == 1
            assert results1[0].success

            # Second dispatch should be rate limited
            results2 = dispatcher.dispatch(mock_healing_result, mock_script_path)
            assert len(results2) == 1
            assert not results2[0].success
            assert "Rate limit" in results2[0].error_message

    def test_add_custom_channel(self):
        """Test adding a custom notification channel."""
        config = NotificationConfig()
        dispatcher = NotificationDispatcher(config)

        # Create a mock channel
        mock_channel = Mock()
        mock_channel.name = "custom"

        dispatcher.add_channel(mock_channel)

        assert dispatcher.get_channel_count() == 1
        assert "custom" in dispatcher.get_channel_names()
