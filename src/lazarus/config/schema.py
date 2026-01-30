"""Configuration schema using Pydantic v2."""

from __future__ import annotations

import re
from enum import Enum
from ipaddress import AddressValueError, ip_address
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


class ScriptType(str, Enum):
    """Type of script for timeout defaults."""

    PYTHON = "python"
    SHELL = "shell"
    NODE = "node"
    OTHER = "other"


# Default timeouts in seconds for each script type
DEFAULT_TIMEOUTS = {
    ScriptType.PYTHON: 60,
    ScriptType.SHELL: 180,  # Shell scripts need longer
    ScriptType.NODE: 90,
    ScriptType.OTHER: 120,
}


class ScriptConfig(BaseModel):
    """Configuration for an individual script to monitor and heal.

    Attributes:
        name: Human-readable name for the script
        path: Path to the script file relative to repository root
        description: Optional description of what the script does
        schedule: Optional cron schedule expression for scheduled runs
        script_type: Type of script for timeout defaults
        timeout: Maximum execution time in seconds (default based on script_type)
        working_dir: Optional working directory for script execution
        allowed_files: Files that Claude Code is allowed to modify
        forbidden_files: Files that Claude Code must never modify
        environment: Required environment variable names (values from system)
        setup_commands: Commands to run before executing the script
        custom_prompt: Additional context to provide to Claude Code
        idempotent: Whether the script is safe to re-run (default: True)
        success_criteria: Custom success validation beyond exit code
    """

    name: str = Field(description="Human-readable name for the script")
    path: Path = Field(description="Path to the script file")
    description: str | None = Field(
        default=None, description="Description of what the script does"
    )
    schedule: str | None = Field(
        default=None,
        description="Cron schedule expression (e.g., '0 */6 * * *')",
    )
    script_type: ScriptType = Field(
        default=ScriptType.OTHER,
        description="Type of script for timeout defaults"
    )
    timeout: int | None = Field(
        default=None, ge=1, le=86400, description="Execution timeout in seconds"
    )
    working_dir: Path | None = Field(
        default=None, description="Working directory for script execution"
    )
    allowed_files: list[str] = Field(
        default_factory=list,
        description="Glob patterns for files Claude Code can modify",
    )
    forbidden_files: list[str] = Field(
        default_factory=list,
        description="Glob patterns for files Claude Code must not modify",
    )
    environment: list[str] = Field(
        default_factory=list, description="Required environment variable names"
    )
    setup_commands: list[str] = Field(
        default_factory=list, description="Commands to run before script execution"
    )
    custom_prompt: str | None = Field(
        default=None, description="Additional context for Claude Code"
    )
    idempotent: bool = Field(
        default=True, description="Whether the script is safe to re-run"
    )
    success_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Custom success validation (e.g., {'contains': 'Success'})",
    )

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        """Validate cron schedule format."""
        if v is None:
            return v
        # Basic cron validation: 5 or 6 fields
        parts = v.split()
        if len(parts) not in (5, 6):
            raise ValueError(
                f"Invalid cron schedule '{v}': must have 5 or 6 fields"
            )
        return v

    @model_validator(mode="after")
    def set_default_timeout(self) -> ScriptConfig:
        """Set timeout based on script_type if not explicitly provided."""
        if self.timeout is None:
            self.timeout = DEFAULT_TIMEOUTS[self.script_type]
        return self


class HealingConfig(BaseModel):
    """Configuration for the healing process.

    Attributes:
        max_attempts: Maximum number of healing attempts (default: 3)
        timeout_per_attempt: Maximum time for each attempt in seconds (default: 300)
        total_timeout: Maximum total time for all attempts in seconds (default: 900)
        claude_model: Claude model to use (default: claude-sonnet-4-5-20250929)
        max_turns: Maximum conversation turns per healing session (default: 30)
        allowed_tools: Specific tools Claude Code can use (empty = all)
        forbidden_tools: Tools Claude Code cannot use
    """

    max_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum healing attempts"
    )
    timeout_per_attempt: int = Field(
        default=300, ge=30, le=3600, description="Timeout per attempt in seconds"
    )
    total_timeout: int = Field(
        default=900, ge=60, le=7200, description="Total timeout in seconds"
    )
    claude_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use for healing",
    )
    max_turns: int = Field(
        default=30, ge=1, le=100, description="Maximum conversation turns"
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Specific tools Claude Code can use (empty = all)",
    )
    forbidden_tools: list[str] = Field(
        default_factory=list, description="Tools Claude Code cannot use"
    )

    @model_validator(mode="after")
    def validate_timeouts(self) -> HealingConfig:
        """Ensure total timeout is reasonable compared to per-attempt timeout."""
        if self.total_timeout < self.timeout_per_attempt:
            raise ValueError(
                "total_timeout must be >= timeout_per_attempt"
            )
        return self


class SlackConfig(BaseModel):
    """Slack notification configuration.

    Attributes:
        webhook_url: Slack webhook URL (supports ${ENV_VAR} expansion)
        channel: Optional channel override
        on_success: Send notifications on successful healing (default: True)
        on_failure: Send notifications on healing failure (default: True)
    """

    webhook_url: Annotated[str, Field(description="Slack webhook URL")]
    channel: str | None = Field(default=None, description="Channel override")
    on_success: bool = Field(default=True, description="Notify on success")
    on_failure: bool = Field(default=True, description="Notify on failure")

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate webhook URL to prevent SSRF attacks.

        This validator ensures the webhook URL:
        - Uses HTTP or HTTPS protocol only
        - Does not point to localhost or loopback addresses
        - Does not point to private IP ranges (RFC 1918)
        - Does not point to cloud metadata endpoints

        Args:
            v: The webhook URL to validate

        Returns:
            The validated URL

        Raises:
            ValueError: If the URL is invalid or potentially dangerous
        """
        # Skip validation for environment variable placeholders
        if v.startswith("${") and v.endswith("}"):
            return v

        # Check protocol
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must use HTTP or HTTPS protocol")

        # Parse and check hostname
        parsed = urlparse(v)
        hostname = parsed.hostname
        if hostname:
            # Block cloud metadata endpoints (check before private IP check for specific error)
            if hostname == "169.254.169.254":
                raise ValueError("Webhook URL cannot point to cloud metadata endpoint")

            # Block localhost variants
            if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                raise ValueError("Webhook URL cannot point to localhost")

            # Check if IP address and block private ranges
            try:
                ip = ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError(
                        f"Webhook URL cannot point to private IP: {hostname}"
                    )
            except (AddressValueError, ValueError) as e:
                # Not an IP address, check if it's a ValueError from our validation
                if "Webhook URL cannot point to private IP" in str(e):
                    raise
                # Otherwise, it's a hostname which is OK
                pass

        return v


class DiscordConfig(BaseModel):
    """Discord notification configuration.

    Attributes:
        webhook_url: Discord webhook URL (supports ${ENV_VAR} expansion)
        on_success: Send notifications on successful healing (default: True)
        on_failure: Send notifications on healing failure (default: True)
    """

    webhook_url: Annotated[str, Field(description="Discord webhook URL")]
    on_success: bool = Field(default=True, description="Notify on success")
    on_failure: bool = Field(default=True, description="Notify on failure")

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate webhook URL to prevent SSRF attacks.

        This validator ensures the webhook URL:
        - Uses HTTP or HTTPS protocol only
        - Does not point to localhost or loopback addresses
        - Does not point to private IP ranges (RFC 1918)
        - Does not point to cloud metadata endpoints

        Args:
            v: The webhook URL to validate

        Returns:
            The validated URL

        Raises:
            ValueError: If the URL is invalid or potentially dangerous
        """
        # Skip validation for environment variable placeholders
        if v.startswith("${") and v.endswith("}"):
            return v

        # Check protocol
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must use HTTP or HTTPS protocol")

        # Parse and check hostname
        parsed = urlparse(v)
        hostname = parsed.hostname
        if hostname:
            # Block cloud metadata endpoints (check before private IP check for specific error)
            if hostname == "169.254.169.254":
                raise ValueError("Webhook URL cannot point to cloud metadata endpoint")

            # Block localhost variants
            if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                raise ValueError("Webhook URL cannot point to localhost")

            # Check if IP address and block private ranges
            try:
                ip = ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError(
                        f"Webhook URL cannot point to private IP: {hostname}"
                    )
            except (AddressValueError, ValueError) as e:
                # Not an IP address, check if it's a ValueError from our validation
                if "Webhook URL cannot point to private IP" in str(e):
                    raise
                # Otherwise, it's a hostname which is OK
                pass

        return v


class EmailConfig(BaseModel):
    """Email notification configuration.

    Attributes:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port (default: 587)
        username: SMTP username (supports ${ENV_VAR} expansion)
        password: SMTP password (supports ${ENV_VAR} expansion)
        from_addr: Sender email address
        to_addrs: List of recipient email addresses
        on_success: Send notifications on successful healing (default: True)
        on_failure: Send notifications on healing failure (default: True)
        use_tls: Use TLS encryption (default: True)
    """

    smtp_host: str = Field(description="SMTP server hostname")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    username: str | None = Field(
        default=None, description="SMTP username (supports ${ENV_VAR})"
    )
    password: str | None = Field(
        default=None, description="SMTP password (supports ${ENV_VAR})"
    )
    from_addr: str = Field(description="Sender email address")
    to_addrs: list[str] = Field(description="Recipient email addresses")
    on_success: bool = Field(default=True, description="Notify on success")
    on_failure: bool = Field(default=True, description="Notify on failure")
    use_tls: bool = Field(default=True, description="Use TLS encryption")


class GitHubIssuesConfig(BaseModel):
    """GitHub Issues notification configuration.

    Attributes:
        repo: Repository in format 'owner/repo'
        labels: Labels to apply to created issues
        on_failure: Create issues on healing failure (default: True)
        assignees: Optional list of users to assign issues to
    """

    repo: str = Field(
        description="Repository in format 'owner/repo'",
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
    )
    labels: list[str] = Field(
        default_factory=lambda: ["lazarus", "auto-heal"],
        description="Labels for issues",
    )
    on_failure: bool = Field(default=True, description="Create issues on failure")
    assignees: list[str] = Field(
        default_factory=list, description="Users to assign issues to"
    )


class WebhookConfig(BaseModel):
    """Custom webhook notification configuration.

    Attributes:
        url: Webhook URL (supports ${ENV_VAR} expansion)
        headers: Optional HTTP headers to send
        on_success: Send notifications on successful healing (default: True)
        on_failure: Send notifications on healing failure (default: True)
        method: HTTP method to use (default: POST)
    """

    url: Annotated[str, Field(description="Webhook URL")]
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers"
    )
    on_success: bool = Field(default=True, description="Notify on success")
    on_failure: bool = Field(default=True, description="Notify on failure")
    method: str = Field(
        default="POST", pattern=r"^(GET|POST|PUT|PATCH)$", description="HTTP method"
    )

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate webhook URL to prevent SSRF attacks.

        This validator ensures the webhook URL:
        - Uses HTTP or HTTPS protocol only
        - Does not point to localhost or loopback addresses
        - Does not point to private IP ranges (RFC 1918)
        - Does not point to cloud metadata endpoints

        Args:
            v: The webhook URL to validate

        Returns:
            The validated URL

        Raises:
            ValueError: If the URL is invalid or potentially dangerous
        """
        # Skip validation for environment variable placeholders
        if v.startswith("${") and v.endswith("}"):
            return v

        # Check protocol
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must use HTTP or HTTPS protocol")

        # Parse and check hostname
        parsed = urlparse(v)
        hostname = parsed.hostname
        if hostname:
            # Block cloud metadata endpoints (check before private IP check for specific error)
            if hostname == "169.254.169.254":
                raise ValueError("Webhook URL cannot point to cloud metadata endpoint")

            # Block localhost variants
            if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                raise ValueError("Webhook URL cannot point to localhost")

            # Check if IP address and block private ranges
            try:
                ip = ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError(
                        f"Webhook URL cannot point to private IP: {hostname}"
                    )
            except (AddressValueError, ValueError) as e:
                # Not an IP address, check if it's a ValueError from our validation
                if "Webhook URL cannot point to private IP" in str(e):
                    raise
                # Otherwise, it's a hostname which is OK
                pass

        return v


class NotificationConfig(BaseModel):
    """Notification configuration for various channels.

    Attributes:
        slack: Optional Slack notification configuration
        discord: Optional Discord notification configuration
        email: Optional email notification configuration
        github_issues: Optional GitHub Issues notification configuration
        webhook: Optional custom webhook notification configuration
    """

    slack: SlackConfig | None = Field(default=None, description="Slack notifications")
    discord: DiscordConfig | None = Field(
        default=None, description="Discord notifications"
    )
    email: EmailConfig | None = Field(default=None, description="Email notifications")
    github_issues: GitHubIssuesConfig | None = Field(
        default=None, description="GitHub Issues notifications"
    )
    webhook: WebhookConfig | None = Field(
        default=None, description="Custom webhook notifications"
    )


class GitConfig(BaseModel):
    """Git and pull request configuration.

    Attributes:
        create_pr: Whether to create PRs automatically (default: True)
        branch_prefix: Prefix for healing branches (default: 'lazarus/fix')
        draft_pr: Create PRs as drafts (default: False)
        auto_merge: Enable auto-merge if checks pass (default: False)
        commit_message_template: Template for commit messages
        pr_title_template: Template for PR titles
        pr_body_template: Template for PR bodies
    """

    create_pr: bool = Field(
        default=True, description="Create pull requests automatically"
    )
    branch_prefix: str = Field(
        default="lazarus/fix", description="Prefix for healing branches"
    )
    draft_pr: bool = Field(default=False, description="Create PRs as drafts")
    auto_merge: bool = Field(
        default=False, description="Enable auto-merge if checks pass"
    )
    commit_message_template: str | None = Field(
        default=None, description="Template for commit messages"
    )
    pr_title_template: str | None = Field(
        default=None, description="Template for PR titles"
    )
    pr_body_template: str | None = Field(
        default=None, description="Template for PR bodies"
    )


class SecurityConfig(BaseModel):
    """Security and secrets redaction configuration.

    Attributes:
        redact_patterns: Built-in regex patterns for secret detection
        additional_patterns: User-defined regex patterns for secret detection
        safe_env_vars: Environment variables that are safe to expose
    """

    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)(api[_-]?key|apikey)[\s=:]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            r"(?i)(token|access[_-]?token)[\s=:]+['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?",
            r"(?i)(secret|client[_-]?secret)[\s=:]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            r"(?i)(password|passwd|pwd)[\s=:]+['\"]?([^\s'\"]{8,})['\"]?",
            r"(?i)(bearer\s+[a-zA-Z0-9_\-\.]+)",
            r"(?i)(authorization:\s*[a-zA-Z0-9_\-\.]+)",
            r"(?i)(aws[_-]?access[_-]?key[_-]?id)[\s=:]+['\"]?([A-Z0-9]{20})['\"]?",
            r"(?i)(aws[_-]?secret[_-]?access[_-]?key)[\s=:]+['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
            r"(?i)(private[_-]?key|rsa[_-]?private[_-]?key)",
            r"(?i)(BEGIN\s+(RSA\s+)?PRIVATE\s+KEY)",
        ],
        description="Built-in regex patterns for secret detection",
    )
    additional_patterns: list[str] = Field(
        default_factory=list, description="User-defined regex patterns"
    )
    safe_env_vars: list[str] = Field(
        default_factory=lambda: [
            "PATH",
            "HOME",
            "USER",
            "SHELL",
            "LANG",
            "PWD",
            "TERM",
        ],
        description="Environment variables safe to expose",
    )

    @field_validator("redact_patterns", "additional_patterns")
    @classmethod
    def validate_regex_patterns(cls, v: list[str]) -> list[str]:
        """Validate that all patterns are valid regex."""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e
        return v


class LoggingConfig(BaseModel):
    """Logging configuration.

    Attributes:
        level: Log level (default: INFO)
        format: Log format string
        file: Optional log file path
        rotation: Log rotation size in MB (0 = no rotation)
        retention: Number of rotated logs to keep (default: 10)
        console: Log to console (default: True)
    """

    level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Log level",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file: Path | None = Field(default=None, description="Log file path")
    rotation: int = Field(
        default=10, ge=0, le=1000, description="Log rotation size in MB"
    )
    retention: int = Field(
        default=10, ge=1, le=100, description="Number of rotated logs to keep"
    )
    console: bool = Field(default=True, description="Log to console")


class LazarusConfig(BaseModel):
    """Main Lazarus configuration.

    This is the root configuration object that contains all settings for
    the Lazarus self-healing system.

    Attributes:
        scripts: List of scripts to monitor and heal
        healing: Healing process configuration
        notifications: Notification settings
        git: Git and pull request configuration
        security: Security and secrets redaction configuration
        logging: Logging configuration
    """

    scripts: list[ScriptConfig] = Field(
        default_factory=list, description="Scripts to monitor and heal"
    )
    healing: HealingConfig = Field(
        default_factory=HealingConfig, description="Healing configuration"
    )
    notifications: NotificationConfig = Field(
        default_factory=NotificationConfig, description="Notification settings"
    )
    git: GitConfig = Field(
        default_factory=GitConfig, description="Git configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @model_validator(mode="after")
    def validate_scripts(self) -> LazarusConfig:
        """Validate script configurations."""
        if not self.scripts:
            # This is a warning-level validation; empty scripts list is valid
            # but user probably wants to configure at least one script
            pass

        # Check for duplicate script names
        names = [s.name for s in self.scripts]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(
                f"Duplicate script names found: {', '.join(set(duplicates))}"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scripts": [
                        {
                            "name": "daily-backup",
                            "path": "scripts/backup.sh",
                            "description": "Daily database backup",
                            "schedule": "0 2 * * *",
                            "timeout": 600,
                        }
                    ],
                    "healing": {
                        "max_attempts": 3,
                        "timeout_per_attempt": 300,
                        "total_timeout": 900,
                    },
                    "notifications": {
                        "slack": {
                            "webhook_url": "${SLACK_WEBHOOK_URL}",
                            "on_success": True,
                            "on_failure": True,
                        }
                    },
                }
            ]
        }
    }
