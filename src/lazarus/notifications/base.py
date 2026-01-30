"""Base classes and protocols for notification channels.

This module defines the core interfaces and data structures for the notification system.
All notification channels implement the NotificationChannel protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from lazarus.core.healer import HealingResult


@dataclass
class NotificationResult:
    """Result of sending a notification to a channel.

    Attributes:
        success: Whether the notification was sent successfully
        channel_name: Name of the notification channel (e.g., "slack", "discord")
        error_message: Error message if notification failed, None if successful
    """

    success: bool
    channel_name: str
    error_message: Optional[str] = None


class NotificationChannel(Protocol):
    """Protocol for notification channels.

    All notification channels must implement this interface to be compatible
    with the NotificationDispatcher.
    """

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send a notification about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if notification was sent successfully, False otherwise

        Note:
            Implementations should handle exceptions internally and return False
            on failure rather than raising exceptions.
        """
        ...

    @property
    def name(self) -> str:
        """Get the name of this notification channel.

        Returns:
            Channel name (e.g., "slack", "discord", "email")
        """
        ...
