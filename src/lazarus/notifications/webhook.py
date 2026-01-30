"""Custom webhook notification channel implementation.

This module provides generic webhook notifications with customizable payloads.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from lazarus.config.schema import WebhookConfig
from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Custom webhook notification channel.

    Sends JSON payloads to custom webhook URLs with configurable headers
    and HTTP methods.

    Attributes:
        config: Webhook configuration including URL, headers, and method
        timeout: HTTP request timeout in seconds (default: 10)
    """

    def __init__(self, config: WebhookConfig, timeout: int = 10) -> None:
        """Initialize Webhook notifier.

        Args:
            config: Webhook configuration
            timeout: HTTP request timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._name = "webhook"

    @property
    def name(self) -> str:
        """Get the name of this notification channel."""
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send a webhook notification about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Check if we should send based on success/failure
        if result.success and not self.config.on_success:
            logger.debug("Skipping webhook notification for successful healing (disabled)")
            return True

        if not result.success and not self.config.on_failure:
            logger.debug("Skipping webhook notification for failed healing (disabled)")
            return True

        try:
            payload = self._build_payload(result, script_path)

            with httpx.Client(timeout=self.timeout) as client:
                # Use the configured HTTP method
                method = self.config.method.upper()

                if method == "POST":
                    response = client.post(
                        self.config.url,
                        json=payload,
                        headers=self.config.headers,
                    )
                elif method == "PUT":
                    response = client.put(
                        self.config.url,
                        json=payload,
                        headers=self.config.headers,
                    )
                elif method == "PATCH":
                    response = client.patch(
                        self.config.url,
                        json=payload,
                        headers=self.config.headers,
                    )
                elif method == "GET":
                    # For GET, send payload as query params
                    response = client.get(
                        self.config.url,
                        params=payload,
                        headers=self.config.headers,
                    )
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return False

                response.raise_for_status()

            logger.info(f"Successfully sent webhook notification to {self.config.url}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook notification: {e}")
            return False

    def _build_payload(self, result: HealingResult, script_path: Path) -> dict:
        """Build webhook payload in standard format.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            JSON-serializable payload dict
        """
        # Build attempts summary
        attempts = []
        for attempt in result.attempts:
            attempts.append({
                "attempt_number": attempt.attempt_number,
                "status": attempt.verification.status,
                "duration": attempt.duration,
            })

        # Build standard payload
        payload = {
            "event": "healing_complete",
            "success": result.success,
            "script": {
                "path": str(script_path),
                "name": script_path.name,
            },
            "result": {
                "success": result.success,
                "attempts_count": len(result.attempts),
                "duration": result.duration,
                "error_message": result.error_message,
                "pr_url": result.pr_url,
            },
            "execution": {
                "exit_code": result.final_execution.exit_code,
                "duration": result.final_execution.duration,
                "timestamp": result.final_execution.timestamp.isoformat(),
                # Only include stderr/stdout snippets (truncated)
                "stderr": (
                    result.final_execution.stderr[:500]
                    if result.final_execution.stderr
                    else None
                ),
                "stdout": (
                    result.final_execution.stdout[:500]
                    if result.final_execution.stdout
                    else None
                ),
            },
            "attempts": attempts,
        }

        return payload
