"""Discord notification channel implementation.

This module provides Discord notifications via webhook URLs with embed formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from lazarus.config.schema import DiscordConfig
from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord notification channel using webhook URLs.

    Sends formatted embeds to Discord with color-coded status, error details,
    and PR links when available.

    Attributes:
        config: Discord configuration including webhook URL and notification settings
        timeout: HTTP request timeout in seconds (default: 10)
    """

    def __init__(self, config: DiscordConfig, timeout: int = 10) -> None:
        """Initialize Discord notifier.

        Args:
            config: Discord configuration
            timeout: HTTP request timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._name = "discord"

    @property
    def name(self) -> str:
        """Get the name of this notification channel."""
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send a Discord notification about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Check if we should send based on success/failure
        if result.success and not self.config.on_success:
            logger.debug("Skipping Discord notification for successful healing (disabled)")
            return True

        if not result.success and not self.config.on_failure:
            logger.debug("Skipping Discord notification for failed healing (disabled)")
            return True

        try:
            payload = self._build_payload(result, script_path)

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.config.webhook_url,
                    json=payload,
                )
                response.raise_for_status()

            logger.info("Successfully sent Discord notification")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord notification: {e}")
            return False

    def _build_payload(self, result: HealingResult, script_path: Path) -> dict:
        """Build Discord message payload with embed formatting.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            Discord webhook payload dict
        """
        # Color coding: green for success, red for failure
        color = 0x00FF00 if result.success else 0xFF0000

        # Status text
        status_text = "Healing Successful ✅" if result.success else "Healing Failed ❌"

        # Build embed fields
        fields = [
            {
                "name": "Script",
                "value": f"`{script_path.name}`",
                "inline": True,
            },
            {
                "name": "Attempts",
                "value": str(len(result.attempts)),
                "inline": True,
            },
            {
                "name": "Duration",
                "value": f"{result.duration:.2f}s",
                "inline": True,
            },
            {
                "name": "Exit Code",
                "value": str(result.final_execution.exit_code),
                "inline": True,
            },
        ]

        # Add error message if failed
        if not result.success and result.error_message:
            error_msg = result.error_message
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."

            fields.append(
                {
                    "name": "Error Summary",
                    "value": f"```{error_msg}```",
                    "inline": False,
                }
            )

        # Add stderr snippet if available
        if result.final_execution.stderr:
            stderr = result.final_execution.stderr
            if len(stderr) > 300:
                stderr = stderr[:300] + "..."

            fields.append(
                {
                    "name": "Error Output",
                    "value": f"```{stderr}```",
                    "inline": False,
                }
            )

        # Build embed
        embed = {
            "title": status_text,
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"Script: {script_path}",
            },
            "timestamp": result.final_execution.timestamp.isoformat(),
        }

        # Add PR link if available
        if result.pr_url:
            embed["url"] = result.pr_url
            fields.append(
                {
                    "name": "Pull Request",
                    "value": f"[View PR]({result.pr_url})",
                    "inline": False,
                }
            )

        return {"embeds": [embed]}
