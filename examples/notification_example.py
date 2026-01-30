#!/usr/bin/env python3
"""Example demonstrating the Lazarus notification system.

This example shows how to configure and use various notification channels
to receive alerts about healing results.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

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
from lazarus.notifications import NotificationDispatcher


def create_sample_healing_result(success: bool = False) -> HealingResult:
    """Create a sample healing result for demonstration.

    Args:
        success: Whether the healing was successful

    Returns:
        Sample HealingResult
    """
    execution_result = ExecutionResult(
        exit_code=0 if success else 1,
        stdout="Sample output",
        stderr="" if success else "Error: Something went wrong",
        duration=2.5,
        timestamp=datetime.now(UTC),
    )

    return HealingResult(
        success=success,
        attempts=[],
        final_execution=execution_result,
        pr_url="https://github.com/example/repo/pull/42" if not success else None,
        duration=5.0,
        error_message=None if success else "Healing failed after 3 attempts",
    )


def example_slack_only():
    """Example: Configure Slack notifications only."""
    print("\n=== Slack Only Example ===")

    # Configure Slack notifications
    # Note: Replace with your actual Slack webhook URL or use environment variable
    config = NotificationConfig(
        slack=SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"),
            on_success=True,
            on_failure=True,
            channel="#alerts",  # Optional channel override
        )
    )

    dispatcher = NotificationDispatcher(config)
    result = create_sample_healing_result(success=False)
    script_path = Path("/path/to/script.py")

    print(f"Configured channels: {dispatcher.get_channel_names()}")
    print("Sending notification...")

    # Send notification
    notification_results = dispatcher.dispatch(result, script_path)

    for nr in notification_results:
        print(f"  {nr.channel_name}: {'✅' if nr.success else '❌'}")


def example_multi_channel():
    """Example: Configure multiple notification channels."""
    print("\n=== Multi-Channel Example ===")

    config = NotificationConfig(
        # Slack
        slack=SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"),
            on_success=True,
            on_failure=True,
        ),
        # Discord
        discord=DiscordConfig(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"),
            on_success=False,  # Only send on failure
            on_failure=True,
        ),
        # Email
        email=EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username=os.getenv("SMTP_USERNAME", "your-email@gmail.com"),
            password=os.getenv("SMTP_PASSWORD", "your-app-password"),
            from_addr="lazarus@example.com",
            to_addrs=["admin@example.com", "team@example.com"],
            use_tls=True,
            on_success=False,  # Only send on failure
            on_failure=True,
        ),
        # GitHub Issues (only on failure)
        github_issues=GitHubIssuesConfig(
            repo="owner/repo",
            labels=["lazarus", "auto-heal", "bug"],
            on_failure=True,
            assignees=["maintainer1", "maintainer2"],
        ),
        # Custom webhook
        webhook=WebhookConfig(
            url="https://your-api.com/webhooks/lazarus",
            method="POST",
            headers={
                "Authorization": f"Bearer {os.getenv('WEBHOOK_TOKEN', 'your-token')}",
                "Content-Type": "application/json",
            },
            on_success=True,
            on_failure=True,
        ),
    )

    dispatcher = NotificationDispatcher(config)
    result = create_sample_healing_result(success=False)
    script_path = Path("/path/to/production/script.sh")

    print(f"Configured {dispatcher.get_channel_count()} channels:")
    for channel in dispatcher.get_channel_names():
        print(f"  - {channel}")

    print("\nSending notifications...")

    # Send notification to all channels
    notification_results = dispatcher.dispatch(result, script_path)

    print("\nResults:")
    for nr in notification_results:
        status = "✅ Success" if nr.success else f"❌ Failed: {nr.error_message}"
        print(f"  {nr.channel_name}: {status}")


def example_custom_channel():
    """Example: Add a custom notification channel."""
    print("\n=== Custom Channel Example ===")


    class ConsoleNotifier:
        """Simple console notification channel for demonstration."""

        def __init__(self):
            self._name = "console"

        @property
        def name(self) -> str:
            return self._name

        def send(self, result: HealingResult, script_path: Path) -> bool:
            """Print notification to console."""
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            print(f"\n{'='*60}")
            print(f"NOTIFICATION: {status}")
            print(f"Script: {script_path}")
            print(f"Attempts: {len(result.attempts)}")
            print(f"Duration: {result.duration:.2f}s")
            if result.error_message:
                print(f"Error: {result.error_message}")
            if result.pr_url:
                print(f"PR: {result.pr_url}")
            print(f"{'='*60}\n")
            return True

    # Start with basic config
    config = NotificationConfig()
    dispatcher = NotificationDispatcher(config)

    # Add custom channel
    custom_channel = ConsoleNotifier()
    dispatcher.add_channel(custom_channel)

    result = create_sample_healing_result(success=False)
    script_path = Path("/path/to/script.py")

    print(f"Channels: {dispatcher.get_channel_names()}")

    # Send notification
    dispatcher.dispatch(result, script_path)


def example_success_vs_failure():
    """Example: Different notifications for success vs failure."""
    print("\n=== Success vs Failure Example ===")

    config = NotificationConfig(
        slack=SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"),
            on_success=True,  # Notify on success
            on_failure=True,  # Notify on failure
        ),
        discord=DiscordConfig(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"),
            on_success=False,  # Don't notify on success
            on_failure=True,   # Only notify on failure
        ),
    )

    dispatcher = NotificationDispatcher(config)
    script_path = Path("/path/to/script.py")

    # Test with successful healing
    print("\n1. Successful healing:")
    success_result = create_sample_healing_result(success=True)
    results = dispatcher.dispatch(success_result, script_path)
    print(f"  Slack sent: {any(r.channel_name == 'slack' and r.success for r in results)}")
    print(f"  Discord sent: {any(r.channel_name == 'discord' and r.success for r in results)}")

    # Test with failed healing
    print("\n2. Failed healing:")
    failure_result = create_sample_healing_result(success=False)
    results = dispatcher.dispatch(failure_result, script_path)
    print(f"  Slack sent: {any(r.channel_name == 'slack' and r.success for r in results)}")
    print(f"  Discord sent: {any(r.channel_name == 'discord' and r.success for r in results)}")


def main():
    """Run all examples."""
    print("Lazarus Notification System Examples")
    print("=" * 60)

    # Note: Most examples won't actually send notifications unless you
    # configure real webhook URLs via environment variables

    # Example 1: Slack only
    # example_slack_only()

    # Example 2: Multiple channels
    # example_multi_channel()

    # Example 3: Custom channel (works without configuration)
    example_custom_channel()

    # Example 4: Success vs failure
    # example_success_vs_failure()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("\nTo actually send notifications, set these environment variables:")
    print("  - SLACK_WEBHOOK_URL")
    print("  - DISCORD_WEBHOOK_URL")
    print("  - SMTP_USERNAME")
    print("  - SMTP_PASSWORD")
    print("  - WEBHOOK_TOKEN")


if __name__ == "__main__":
    main()
