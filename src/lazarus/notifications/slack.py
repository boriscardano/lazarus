"""Slack notification channel implementation.

This module provides Slack notifications via webhook URLs with rich message formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from lazarus.config.schema import SlackConfig
from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack notification channel using webhook URLs.

    Sends rich formatted messages to Slack with status indicators, error details,
    and PR links when available.

    Attributes:
        config: Slack configuration including webhook URL and notification settings
        timeout: HTTP request timeout in seconds (default: 10)
    """

    def __init__(self, config: SlackConfig, timeout: int = 10) -> None:
        """Initialize Slack notifier.

        Args:
            config: Slack configuration
            timeout: HTTP request timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._name = "slack"

    @property
    def name(self) -> str:
        """Get the name of this notification channel."""
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send a Slack notification about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Check if we should send based on success/failure
        if result.success and not self.config.on_success:
            logger.debug("Skipping Slack notification for successful healing (disabled)")
            return True

        if not result.success and not self.config.on_failure:
            logger.debug("Skipping Slack notification for failed healing (disabled)")
            return True

        try:
            payload = self._build_payload(result, script_path)

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.config.webhook_url,
                    json=payload,
                )
                response.raise_for_status()

            logger.info("Successfully sent Slack notification")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            return False

    def _build_payload(self, result: HealingResult, script_path: Path) -> dict:
        """Build Slack message payload with rich formatting.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            Slack message payload dict
        """
        # Status indicator
        status_emoji = "✅" if result.success else "❌"
        status_text = "Healing Successful" if result.success else "Healing Failed"

        # Build blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} {status_text}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Script:*\n`{script_path.name}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Attempts:*\n{len(result.attempts)}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:*\n{result.duration:.2f}s",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Exit Code:*\n{result.final_execution.exit_code}",
                    },
                ],
            },
        ]

        # Add error summary if failed
        if not result.success and result.error_message:
            # Truncate error message if too long
            error_msg = result.error_message
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error Summary:*\n```{error_msg}```",
                    },
                }
            )

        # Add stderr snippet if available
        if result.final_execution.stderr:
            stderr = result.final_execution.stderr
            if len(stderr) > 300:
                stderr = stderr[:300] + "..."

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error Output:*\n```{stderr}```",
                    },
                }
            )

        # Add PR link if available
        if result.pr_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Pull Request:*\n<{result.pr_url}|View PR>",
                    },
                }
            )

        # Add divider and footer
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Script: `{script_path}` | Timestamp: {result.final_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    }
                ],
            }
        )

        payload = {"blocks": blocks}

        # Add channel override if specified
        if self.config.channel:
            payload["channel"] = self.config.channel

        return payload
