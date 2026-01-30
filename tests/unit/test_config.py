"""Unit tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lazarus.config.loader import ConfigError, load_config, validate_config_file
from lazarus.config.schema import (
    DiscordConfig,
    GitConfig,
    HealingConfig,
    LazarusConfig,
    LoggingConfig,
    NotificationConfig,
    ScriptConfig,
    SecurityConfig,
    SlackConfig,
    WebhookConfig,
)


class TestScriptConfig:
    """Tests for ScriptConfig schema."""

    def test_script_config_minimal(self):
        """Test creating minimal script config."""
        config = ScriptConfig(
            name="test-script",
            path=Path("scripts/test.py"),
        )

        assert config.name == "test-script"
        assert config.path == Path("scripts/test.py")
        assert config.timeout == 120  # Default for ScriptType.OTHER
        assert config.idempotent is True  # Default

    def test_script_config_full(self):
        """Test creating full script config."""
        config = ScriptConfig(
            name="test-script",
            path=Path("scripts/test.py"),
            description="Test script",
            schedule="0 */6 * * *",
            timeout=600,
            working_dir=Path("/tmp"),
            allowed_files=["*.py"],
            forbidden_files=[".env"],
            environment=["API_KEY"],
            setup_commands=["pip install -r requirements.txt"],
            custom_prompt="Fix carefully",
            idempotent=False,
        )

        assert config.name == "test-script"
        assert config.timeout == 600
        assert config.working_dir == Path("/tmp")
        assert len(config.allowed_files) == 1
        assert config.idempotent is False

    def test_script_config_invalid_schedule(self):
        """Test invalid cron schedule validation."""
        with pytest.raises(ValidationError, match="Invalid cron schedule"):
            ScriptConfig(
                name="test",
                path=Path("test.py"),
                schedule="invalid cron",
            )

    def test_script_config_timeout_bounds(self):
        """Test timeout boundary validation."""
        # Too low
        with pytest.raises(ValidationError):
            ScriptConfig(
                name="test",
                path=Path("test.py"),
                timeout=0,
            )

        # Too high
        with pytest.raises(ValidationError):
            ScriptConfig(
                name="test",
                path=Path("test.py"),
                timeout=100000,
            )


class TestHealingConfig:
    """Tests for HealingConfig schema."""

    def test_healing_config_defaults(self):
        """Test default healing config values."""
        config = HealingConfig()

        assert config.max_attempts == 3
        assert config.timeout_per_attempt == 300
        assert config.total_timeout == 900
        assert config.claude_model == "claude-sonnet-4-5-20250929"
        assert config.max_turns == 30

    def test_healing_config_custom(self):
        """Test custom healing config."""
        config = HealingConfig(
            max_attempts=5,
            timeout_per_attempt=600,
            total_timeout=3000,
            claude_model="claude-opus-4",
            max_turns=50,
        )

        assert config.max_attempts == 5
        assert config.timeout_per_attempt == 600
        assert config.total_timeout == 3000

    def test_healing_config_timeout_validation(self):
        """Test timeout validation in healing config."""
        # total_timeout must be >= timeout_per_attempt
        with pytest.raises(ValidationError, match="total_timeout"):
            HealingConfig(
                timeout_per_attempt=500,
                total_timeout=300,  # Less than per_attempt
            )


class TestNotificationConfig:
    """Tests for notification configurations."""

    def test_slack_config(self):
        """Test Slack notification config."""
        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            channel="#alerts",
            on_success=True,
            on_failure=True,
        )

        assert config.webhook_url == "https://hooks.slack.com/test"
        assert config.channel == "#alerts"
        assert config.on_success is True

    def test_notification_config_empty(self):
        """Test empty notification config."""
        config = NotificationConfig()

        assert config.slack is None
        assert config.discord is None
        assert config.email is None

    def test_notification_config_with_slack(self):
        """Test notification config with Slack."""
        config = NotificationConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test")
        )

        assert config.slack is not None
        assert config.slack.webhook_url == "https://hooks.slack.com/test"


class TestSSRFProtection:
    """Tests for SSRF protection in webhook URLs."""

    def test_webhook_config_valid_https_url(self):
        """Test that valid HTTPS URLs are accepted."""
        config = WebhookConfig(url="https://api.example.com/webhook")
        assert config.url == "https://api.example.com/webhook"

    def test_webhook_config_valid_http_url(self):
        """Test that valid HTTP URLs are accepted."""
        config = WebhookConfig(url="http://api.example.com/webhook")
        assert config.url == "http://api.example.com/webhook"

    def test_webhook_config_env_var_placeholder(self):
        """Test that environment variable placeholders bypass validation."""
        config = WebhookConfig(url="${WEBHOOK_URL}")
        assert config.url == "${WEBHOOK_URL}"

    def test_webhook_config_rejects_file_protocol(self):
        """Test that file:// protocol is rejected."""
        with pytest.raises(ValidationError, match="must use HTTP or HTTPS"):
            WebhookConfig(url="file:///etc/passwd")

    def test_webhook_config_rejects_gopher_protocol(self):
        """Test that gopher:// protocol is rejected."""
        with pytest.raises(ValidationError, match="must use HTTP or HTTPS"):
            WebhookConfig(url="gopher://example.com")

    def test_webhook_config_rejects_localhost(self):
        """Test that localhost is rejected."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            WebhookConfig(url="http://localhost:8080/webhook")

    def test_webhook_config_rejects_127_0_0_1(self):
        """Test that 127.0.0.1 is rejected."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            WebhookConfig(url="http://127.0.0.1/webhook")

    def test_webhook_config_rejects_ipv6_loopback(self):
        """Test that IPv6 loopback (::1) is rejected."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            WebhookConfig(url="http://[::1]/webhook")

    def test_webhook_config_rejects_0_0_0_0(self):
        """Test that 0.0.0.0 is rejected."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            WebhookConfig(url="http://0.0.0.0/webhook")

    def test_webhook_config_rejects_private_ip_192_168(self):
        """Test that private IP 192.168.x.x is rejected."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            WebhookConfig(url="http://192.168.1.1/webhook")

    def test_webhook_config_rejects_private_ip_10_0(self):
        """Test that private IP 10.x.x.x is rejected."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            WebhookConfig(url="http://10.0.0.1/webhook")

    def test_webhook_config_rejects_private_ip_172_16(self):
        """Test that private IP 172.16.x.x is rejected."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            WebhookConfig(url="http://172.16.0.1/webhook")

    def test_webhook_config_rejects_cloud_metadata_endpoint(self):
        """Test that cloud metadata endpoint 169.254.169.254 is rejected."""
        with pytest.raises(ValidationError, match="cloud metadata endpoint"):
            WebhookConfig(url="http://169.254.169.254/latest/meta-data")

    def test_webhook_config_rejects_link_local_ip(self):
        """Test that link-local IPs are rejected."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            WebhookConfig(url="http://169.254.1.1/webhook")

    def test_slack_config_valid_webhook_url(self):
        """Test that SlackConfig accepts valid webhook URLs."""
        config = SlackConfig(webhook_url="https://hooks.slack.com/services/ABC/XYZ")
        assert "hooks.slack.com" in config.webhook_url

    def test_slack_config_rejects_localhost(self):
        """Test that SlackConfig rejects localhost URLs."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            SlackConfig(webhook_url="http://localhost/webhook")

    def test_slack_config_rejects_private_ip(self):
        """Test that SlackConfig rejects private IPs."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            SlackConfig(webhook_url="http://192.168.1.1/webhook")

    def test_slack_config_env_var_placeholder(self):
        """Test that SlackConfig allows environment variable placeholders."""
        config = SlackConfig(webhook_url="${SLACK_WEBHOOK_URL}")
        assert config.webhook_url == "${SLACK_WEBHOOK_URL}"

    def test_discord_config_valid_webhook_url(self):
        """Test that DiscordConfig accepts valid webhook URLs."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123456/abcdef"
        )
        assert "discord.com" in config.webhook_url

    def test_discord_config_rejects_localhost(self):
        """Test that DiscordConfig rejects localhost URLs."""
        with pytest.raises(ValidationError, match="cannot point to localhost"):
            DiscordConfig(webhook_url="http://localhost/webhook")

    def test_discord_config_rejects_private_ip(self):
        """Test that DiscordConfig rejects private IPs."""
        with pytest.raises(ValidationError, match="cannot point to private IP"):
            DiscordConfig(webhook_url="http://10.0.0.1/webhook")

    def test_discord_config_rejects_cloud_metadata(self):
        """Test that DiscordConfig rejects cloud metadata endpoint."""
        with pytest.raises(ValidationError, match="cloud metadata endpoint"):
            DiscordConfig(webhook_url="http://169.254.169.254/meta-data")

    def test_discord_config_env_var_placeholder(self):
        """Test that DiscordConfig allows environment variable placeholders."""
        config = DiscordConfig(webhook_url="${DISCORD_WEBHOOK_URL}")
        assert config.webhook_url == "${DISCORD_WEBHOOK_URL}"

    def test_webhook_config_rejects_ftp_protocol(self):
        """Test that ftp:// protocol is rejected."""
        with pytest.raises(ValidationError, match="must use HTTP or HTTPS"):
            WebhookConfig(url="ftp://example.com/file")

    def test_webhook_config_valid_subdomain(self):
        """Test that valid subdomains are accepted."""
        config = WebhookConfig(url="https://webhook.api.example.com/notify")
        assert config.url == "https://webhook.api.example.com/notify"

    def test_webhook_config_valid_with_port(self):
        """Test that valid URLs with ports are accepted."""
        config = WebhookConfig(url="https://api.example.com:8443/webhook")
        assert config.url == "https://api.example.com:8443/webhook"

    def test_webhook_config_valid_with_path_and_query(self):
        """Test that URLs with paths and query parameters are accepted."""
        config = WebhookConfig(
            url="https://api.example.com/webhook?token=abc&user=test"
        )
        assert "api.example.com" in config.url


class TestGitConfig:
    """Tests for Git configuration."""

    def test_git_config_defaults(self):
        """Test default Git config values."""
        config = GitConfig()

        assert config.create_pr is True
        assert config.branch_prefix == "lazarus/fix"
        assert config.draft_pr is False
        assert config.auto_merge is False

    def test_git_config_custom(self):
        """Test custom Git config."""
        config = GitConfig(
            create_pr=False,
            branch_prefix="auto-fix",
            draft_pr=True,
            auto_merge=True,
        )

        assert config.create_pr is False
        assert config.branch_prefix == "auto-fix"
        assert config.draft_pr is True
        assert config.auto_merge is True


class TestSecurityConfig:
    """Tests for security configuration."""

    def test_security_config_defaults(self):
        """Test default security config."""
        config = SecurityConfig()

        assert len(config.redact_patterns) > 0
        assert len(config.safe_env_vars) > 0
        assert "PATH" in config.safe_env_vars

    def test_security_config_custom_patterns(self):
        """Test adding custom redaction patterns."""
        config = SecurityConfig(
            additional_patterns=[r"CUSTOM_TOKEN=\w+"]
        )

        assert len(config.additional_patterns) == 1

    def test_security_config_invalid_regex(self):
        """Test invalid regex pattern validation."""
        with pytest.raises(ValidationError, match="Invalid regex"):
            SecurityConfig(
                additional_patterns=["[invalid(regex"]
            )


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_logging_config_defaults(self):
        """Test default logging config."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.console is True
        assert config.file is None
        assert config.rotation == 10

    def test_logging_config_custom(self):
        """Test custom logging config."""
        config = LoggingConfig(
            level="DEBUG",
            console=False,
            file=Path("/var/log/lazarus.log"),
            rotation=20,
            retention=5,
        )

        assert config.level == "DEBUG"
        assert config.console is False
        assert config.file == Path("/var/log/lazarus.log")

    def test_logging_config_invalid_level(self):
        """Test invalid log level validation."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestLazarusConfig:
    """Tests for main Lazarus configuration."""

    def test_lazarus_config_minimal(self):
        """Test minimal Lazarus config."""
        config = LazarusConfig()

        assert len(config.scripts) == 0
        assert config.healing is not None
        assert config.notifications is not None
        assert config.git is not None

    def test_lazarus_config_with_scripts(self):
        """Test Lazarus config with scripts."""
        config = LazarusConfig(
            scripts=[
                ScriptConfig(name="test1", path=Path("test1.py")),
                ScriptConfig(name="test2", path=Path("test2.py")),
            ]
        )

        assert len(config.scripts) == 2
        assert config.scripts[0].name == "test1"

    def test_lazarus_config_duplicate_script_names(self):
        """Test validation of duplicate script names."""
        with pytest.raises(ValidationError, match="Duplicate script names"):
            LazarusConfig(
                scripts=[
                    ScriptConfig(name="duplicate", path=Path("test1.py")),
                    ScriptConfig(name="duplicate", path=Path("test2.py")),
                ]
            )


class TestConfigLoader:
    """Tests for configuration loading."""

    def test_load_valid_config(self, temp_config_file):
        """Test loading valid configuration file."""
        config = load_config(temp_config_file)

        assert config is not None
        assert isinstance(config, LazarusConfig)

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file."""
        with pytest.raises(ConfigError, match="not found"):
            load_config(Path("/nonexistent/config.yaml"))

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError):
            load_config(config_file)

    def test_validate_config_file_valid(self, temp_config_file):
        """Test validating valid config file."""
        is_valid, errors = validate_config_file(temp_config_file)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_file_invalid(self, tmp_path):
        """Test validating invalid config file."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("scripts: not-a-list")

        is_valid, errors = validate_config_file(config_file)

        assert is_valid is False
        assert len(errors) > 0

    def test_load_config_with_env_vars(self, tmp_path, monkeypatch):
        """Test loading config with environment variable expansion."""
        # Set environment variable
        monkeypatch.setenv("TEST_WEBHOOK", "https://example.com/webhook")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
scripts:
  - name: test
    path: test.py

notifications:
  slack:
    webhook_url: "${TEST_WEBHOOK}"
"""
        )

        config = load_config(config_file)

        assert config.notifications.slack is not None
        assert "example.com" in config.notifications.slack.webhook_url


class TestConfigExamples:
    """Tests for configuration examples."""

    def test_example_config_is_valid(self):
        """Test that example config in schema is valid."""
        from lazarus.config.schema import LazarusConfig

        # Get example from schema
        examples = LazarusConfig.model_config.get("json_schema_extra", {}).get(
            "examples", []
        )

        assert len(examples) > 0

        # Validate first example
        example = examples[0]
        config = LazarusConfig(**example)

        assert config is not None
        assert len(config.scripts) > 0
