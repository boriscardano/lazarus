"""Notification system for Lazarus.

This module provides multi-channel notification capabilities for healing results.
Supported channels include Slack, Discord, Email, GitHub Issues, and custom webhooks.

Example:
    >>> from lazarus.notifications import NotificationDispatcher
    >>> from lazarus.config.schema import NotificationConfig
    >>>
    >>> config = NotificationConfig(...)
    >>> dispatcher = NotificationDispatcher(config)
    >>> results = dispatcher.dispatch(healing_result, script_path)
"""

from lazarus.notifications.base import NotificationChannel, NotificationResult
from lazarus.notifications.discord import DiscordNotifier
from lazarus.notifications.dispatcher import NotificationDispatcher
from lazarus.notifications.email import EmailNotifier
from lazarus.notifications.github_issues import GitHubIssueNotifier
from lazarus.notifications.slack import SlackNotifier
from lazarus.notifications.webhook import WebhookNotifier

__all__ = [
    "NotificationChannel",
    "NotificationResult",
    "NotificationDispatcher",
    "SlackNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "GitHubIssueNotifier",
    "WebhookNotifier",
]
