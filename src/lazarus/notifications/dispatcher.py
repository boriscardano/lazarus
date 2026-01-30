"""Multi-channel notification dispatcher.

This module provides the NotificationDispatcher class that coordinates sending
notifications across multiple channels with rate limiting and error handling.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from lazarus.config.schema import NotificationConfig
from lazarus.core.healer import HealingResult
from lazarus.notifications.base import NotificationChannel, NotificationResult
from lazarus.notifications.discord import DiscordNotifier
from lazarus.notifications.email import EmailNotifier
from lazarus.notifications.github_issues import GitHubIssueNotifier
from lazarus.notifications.slack import SlackNotifier
from lazarus.notifications.webhook import WebhookNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Multi-channel notification dispatcher.

    Manages sending notifications across multiple configured channels with
    error handling, rate limiting, and logging.

    Attributes:
        config: Notification configuration
        channels: List of active notification channels
        rate_limit_window: Time window for rate limiting in seconds (default: 60)
        rate_limit_max: Maximum notifications per window (default: 10)
    """

    def __init__(
        self,
        config: NotificationConfig,
        rate_limit_window: int = 60,
        rate_limit_max: int = 10,
    ) -> None:
        """Initialize notification dispatcher.

        Args:
            config: Notification configuration
            rate_limit_window: Time window for rate limiting in seconds
            rate_limit_max: Maximum notifications per window
        """
        self.config = config
        self.rate_limit_window = rate_limit_window
        self.rate_limit_max = rate_limit_max
        self.channels: list[NotificationChannel] = []
        self._notification_times: list[float] = []

        # Initialize configured channels
        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """Initialize all configured notification channels."""
        # Slack
        if self.config.slack:
            try:
                channel = SlackNotifier(self.config.slack)
                self.channels.append(channel)
                logger.info("Initialized Slack notification channel")
            except Exception as e:
                logger.error(f"Failed to initialize Slack channel: {e}")

        # Discord
        if self.config.discord:
            try:
                channel = DiscordNotifier(self.config.discord)
                self.channels.append(channel)
                logger.info("Initialized Discord notification channel")
            except Exception as e:
                logger.error(f"Failed to initialize Discord channel: {e}")

        # Email
        if self.config.email:
            try:
                channel = EmailNotifier(self.config.email)
                self.channels.append(channel)
                logger.info("Initialized Email notification channel")
            except Exception as e:
                logger.error(f"Failed to initialize Email channel: {e}")

        # GitHub Issues
        if self.config.github_issues:
            try:
                channel = GitHubIssueNotifier(self.config.github_issues)
                self.channels.append(channel)
                logger.info("Initialized GitHub Issues notification channel")
            except Exception as e:
                logger.error(f"Failed to initialize GitHub Issues channel: {e}")

        # Custom Webhook
        if self.config.webhook:
            try:
                channel = WebhookNotifier(self.config.webhook)
                self.channels.append(channel)
                logger.info("Initialized Webhook notification channel")
            except Exception as e:
                logger.error(f"Failed to initialize Webhook channel: {e}")

        if not self.channels:
            logger.warning("No notification channels configured")

    def dispatch(
        self,
        result: HealingResult,
        script_path: Path,
    ) -> list[NotificationResult]:
        """Dispatch notifications to all configured channels.

        This method sends notifications to all configured channels, continuing
        even if individual channels fail. It also enforces rate limiting to
        prevent notification spam.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            List of NotificationResult objects, one per channel
        """
        # Check rate limiting
        if not self._check_rate_limit():
            logger.warning(
                f"Rate limit exceeded: max {self.rate_limit_max} notifications "
                f"per {self.rate_limit_window}s window"
            )
            return [
                NotificationResult(
                    success=False,
                    channel_name="dispatcher",
                    error_message="Rate limit exceeded",
                )
            ]

        if not self.channels:
            logger.debug("No notification channels configured, skipping notifications")
            return []

        logger.info(
            f"Dispatching notifications to {len(self.channels)} channel(s) "
            f"for script {script_path.name}"
        )

        results: list[NotificationResult] = []

        # Send to all channels, continuing even if one fails
        for channel in self.channels:
            try:
                logger.debug(f"Sending notification to {channel.name} channel")
                success = channel.send(result, script_path)

                notification_result = NotificationResult(
                    success=success,
                    channel_name=channel.name,
                    error_message=None if success else f"Failed to send to {channel.name}",
                )
                results.append(notification_result)

                if success:
                    logger.info(f"Successfully sent notification to {channel.name}")
                else:
                    logger.warning(f"Failed to send notification to {channel.name}")

            except Exception as e:
                logger.error(f"Unexpected error sending to {channel.name}: {e}")
                results.append(
                    NotificationResult(
                        success=False,
                        channel_name=channel.name,
                        error_message=str(e),
                    )
                )

        # Record notification time for rate limiting
        self._record_notification()

        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Notification dispatch complete: {successful}/{len(results)} successful"
        )

        return results

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limit.

        Returns:
            True if we can send a notification, False if rate limited
        """
        current_time = time.time()

        # Remove old notification times outside the window
        cutoff_time = current_time - self.rate_limit_window
        self._notification_times = [
            t for t in self._notification_times if t > cutoff_time
        ]

        # Check if we're at the limit
        return len(self._notification_times) < self.rate_limit_max

    def _record_notification(self) -> None:
        """Record a notification for rate limiting."""
        self._notification_times.append(time.time())

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a custom notification channel.

        This allows adding custom notification channels that aren't part of
        the standard configuration.

        Args:
            channel: Notification channel to add
        """
        self.channels.append(channel)
        logger.info(f"Added custom notification channel: {channel.name}")

    def get_channel_count(self) -> int:
        """Get the number of configured channels.

        Returns:
            Number of active notification channels
        """
        return len(self.channels)

    def get_channel_names(self) -> list[str]:
        """Get names of all configured channels.

        Returns:
            List of channel names
        """
        return [channel.name for channel in self.channels]
