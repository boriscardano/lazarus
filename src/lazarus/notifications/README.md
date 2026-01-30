# Lazarus Notification System

The notification system provides multi-channel alerts for healing results. Get notified about script failures and successful fixes via Slack, Discord, Email, GitHub Issues, or custom webhooks.

## Supported Channels

- **Slack** - Rich formatted messages via webhook
- **Discord** - Embed messages via webhook
- **Email** - HTML and plain text emails via SMTP
- **GitHub Issues** - Automatic issue creation for failures
- **Webhook** - Custom JSON payloads to any URL

## Quick Start

```python
from lazarus.config.schema import NotificationConfig, SlackConfig
from lazarus.notifications import NotificationDispatcher

# Configure notifications
config = NotificationConfig(
    slack=SlackConfig(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        on_success=True,
        on_failure=True,
    )
)

# Create dispatcher
dispatcher = NotificationDispatcher(config)

# Send notification
results = dispatcher.dispatch(healing_result, script_path)
```

## Configuration

### Slack

```python
from lazarus.config.schema import SlackConfig

slack = SlackConfig(
    webhook_url="${SLACK_WEBHOOK_URL}",  # Supports env var expansion
    channel="#alerts",                    # Optional channel override
    on_success=True,                      # Notify on successful healing
    on_failure=True,                      # Notify on failed healing
)
```

**Features:**
- Rich block-based formatting
- Status indicators (✅/❌)
- Error summaries and stderr snippets
- PR links
- Customizable channels

### Discord

```python
from lazarus.config.schema import DiscordConfig

discord = DiscordConfig(
    webhook_url="${DISCORD_WEBHOOK_URL}",
    on_success=True,
    on_failure=True,
)
```

**Features:**
- Color-coded embeds (green/red)
- Formatted fields
- Timestamps
- PR links
- Error details

### Email

```python
from lazarus.config.schema import EmailConfig

email = EmailConfig(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="${SMTP_USERNAME}",
    password="${SMTP_PASSWORD}",
    from_addr="lazarus@example.com",
    to_addrs=["admin@example.com", "team@example.com"],
    use_tls=True,
    on_success=False,  # Only send on failure
    on_failure=True,
)
```

**Features:**
- HTML and plain text versions
- Professional formatting
- Error details and stack traces
- PR links
- TLS/SSL support

### GitHub Issues

```python
from lazarus.config.schema import GitHubIssuesConfig

github_issues = GitHubIssuesConfig(
    repo="owner/repo",
    labels=["lazarus", "auto-heal", "bug"],
    on_failure=True,  # Only create issues on failure
    assignees=["maintainer1"],
)
```

**Features:**
- Automatic issue creation for failures
- Custom labels and assignees
- Error details in issue body
- Healing attempt history
- PR references
- Uses `gh` CLI (must be installed and authenticated)

### Custom Webhook

```python
from lazarus.config.schema import WebhookConfig

webhook = WebhookConfig(
    url="https://your-api.com/webhooks/lazarus",
    method="POST",  # GET, POST, PUT, PATCH
    headers={
        "Authorization": "Bearer ${WEBHOOK_TOKEN}",
        "Content-Type": "application/json",
    },
    on_success=True,
    on_failure=True,
)
```

**Payload Format:**
```json
{
  "event": "healing_complete",
  "success": false,
  "script": {
    "path": "/path/to/script.py",
    "name": "script.py"
  },
  "result": {
    "success": false,
    "attempts_count": 3,
    "duration": 5.0,
    "error_message": "Healing failed...",
    "pr_url": "https://github.com/..."
  },
  "execution": {
    "exit_code": 1,
    "duration": 2.5,
    "timestamp": "2024-01-30T12:00:00Z",
    "stderr": "Error: ...",
    "stdout": "..."
  },
  "attempts": [...]
}
```

## Multi-Channel Setup

Configure multiple channels to ensure you never miss critical failures:

```python
from lazarus.config.schema import (
    NotificationConfig,
    SlackConfig,
    DiscordConfig,
    EmailConfig,
    GitHubIssuesConfig,
)

config = NotificationConfig(
    # Real-time alerts
    slack=SlackConfig(
        webhook_url="${SLACK_WEBHOOK_URL}",
        on_success=True,
        on_failure=True,
    ),
    # Team channel
    discord=DiscordConfig(
        webhook_url="${DISCORD_WEBHOOK_URL}",
        on_success=False,  # Only failures
        on_failure=True,
    ),
    # Email for critical failures
    email=EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="${SMTP_USERNAME}",
        password="${SMTP_PASSWORD}",
        from_addr="lazarus@example.com",
        to_addrs=["oncall@example.com"],
        on_success=False,
        on_failure=True,
    ),
    # Track failures
    github_issues=GitHubIssuesConfig(
        repo="owner/repo",
        labels=["lazarus", "bug"],
        on_failure=True,
    ),
)
```

## Rate Limiting

The dispatcher includes built-in rate limiting to prevent notification spam:

```python
dispatcher = NotificationDispatcher(
    config,
    rate_limit_window=60,   # Time window in seconds
    rate_limit_max=10,      # Max notifications per window
)
```

Default: Maximum 10 notifications per 60 seconds.

## Custom Channels

Create your own notification channels by implementing the `NotificationChannel` protocol:

```python
from pathlib import Path
from lazarus.notifications.base import NotificationChannel
from lazarus.core.healer import HealingResult

class CustomNotifier:
    """Custom notification channel."""

    def __init__(self):
        self._name = "custom"

    @property
    def name(self) -> str:
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send notification.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            True if successful, False otherwise
        """
        try:
            # Your notification logic here
            print(f"Notification: {script_path} - {result.success}")
            return True
        except Exception:
            return False

# Add to dispatcher
dispatcher.add_channel(CustomNotifier())
```

## Environment Variables

Notification configuration supports environment variable expansion:

```yaml
# lazarus.yaml
notifications:
  slack:
    webhook_url: ${SLACK_WEBHOOK_URL}
  email:
    username: ${SMTP_USERNAME}
    password: ${SMTP_PASSWORD}
  webhook:
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
```

Set variables before running:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export SMTP_USERNAME="user@example.com"
export SMTP_PASSWORD="app-password"
export WEBHOOK_TOKEN="secret-token"
```

## Error Handling

The notification system is designed to be resilient:

- **Continue on failure**: If one channel fails, others still receive notifications
- **Timeout protection**: HTTP requests timeout after 10 seconds (configurable)
- **Rate limiting**: Prevents notification spam
- **Detailed logging**: All failures are logged for debugging

```python
# Check results
results = dispatcher.dispatch(healing_result, script_path)

for result in results:
    if not result.success:
        print(f"Failed to send to {result.channel_name}: {result.error_message}")
```

## Best Practices

1. **Use different channels for different priorities**
   - Slack/Discord for real-time team alerts
   - Email for critical failures requiring attention
   - GitHub Issues for tracking and follow-up

2. **Configure on_success/on_failure appropriately**
   - Real-time channels: Both success and failure
   - Email/Issues: Only failures to reduce noise

3. **Use environment variables for secrets**
   - Never commit webhook URLs or credentials
   - Use ${VAR} syntax in configuration

4. **Test your configuration**
   - Verify webhooks are correct
   - Ensure SMTP credentials work
   - Check `gh` CLI is authenticated

5. **Monitor notification failures**
   - Check logs for delivery issues
   - Verify rate limits aren't too restrictive

## Troubleshooting

### Slack notifications not working
- Verify webhook URL is correct
- Check Slack app has correct permissions
- Review Slack API rate limits

### Discord notifications not working
- Verify webhook URL format
- Check Discord server settings
- Ensure webhook hasn't been deleted

### Email notifications not sending
- Verify SMTP credentials
- Check firewall/network settings
- For Gmail, use app-specific password
- Ensure TLS/SSL settings match server

### GitHub Issues not being created
- Install `gh` CLI: `brew install gh`
- Authenticate: `gh auth login`
- Verify repo permissions
- Check rate limits

### Rate limiting too aggressive
```python
# Increase limits
dispatcher = NotificationDispatcher(
    config,
    rate_limit_window=60,
    rate_limit_max=50,  # Increased
)
```

## Examples

See [examples/notification_example.py](/examples/notification_example.py) for complete working examples.
