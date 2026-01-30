"""Integration tests for CLI commands.

Tests the CLI interface using typer's CliRunner to simulate
command-line invocations.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from lazarus.cli import app

runner = CliRunner()


class TestCheckCommand:
    """Test the 'lazarus check' command."""

    def test_check_all_prerequisites_available(self):
        """Test check command when all prerequisites are available."""
        with patch("shutil.which") as mock_which:
            # All tools are available
            mock_which.return_value = "/usr/bin/tool"

            result = runner.invoke(app, ["check"])

            assert result.exit_code == 0
            assert "git" in result.stdout
            assert "gh" in result.stdout
            assert "claude" in result.stdout
            assert "Available" in result.stdout

    def test_check_missing_prerequisites(self):
        """Test check command when prerequisites are missing."""
        with patch("shutil.which") as mock_which:
            # No tools are available
            mock_which.return_value = None

            result = runner.invoke(app, ["check"])

            assert result.exit_code == 1
            assert "Missing" in result.stdout
            assert "Installation Instructions" in result.stdout

    def test_check_verbose(self):
        """Test check command with verbose flag."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/tool"

            result = runner.invoke(app, ["check", "--verbose"])

            assert result.exit_code == 0


class TestInitCommand:
    """Test the 'lazarus init' command."""

    def test_init_minimal_config(self, tmp_path):
        """Test init command creates minimal config."""
        config_file = tmp_path / "lazarus.yaml"

        result = runner.invoke(
            app,
            ["init", "--output", str(config_file)],
        )

        assert result.exit_code == 0
        assert config_file.exists()

        # Check content
        content = config_file.read_text()
        assert "scripts:" in content
        assert "healing:" in content
        assert "max_attempts:" in content

    def test_init_full_config(self, tmp_path):
        """Test init command creates full config."""
        config_file = tmp_path / "lazarus.yaml"

        result = runner.invoke(
            app,
            ["init", "--full", "--output", str(config_file)],
        )

        assert result.exit_code == 0
        assert config_file.exists()

        # Check content includes all sections
        content = config_file.read_text()
        assert "scripts:" in content
        assert "healing:" in content
        assert "notifications:" in content
        assert "git:" in content
        assert "security:" in content
        assert "logging:" in content

    def test_init_refuses_overwrite_without_force(self, tmp_path):
        """Test init refuses to overwrite existing file without --force."""
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text("existing content")

        result = runner.invoke(
            app,
            ["init", "--output", str(config_file)],
        )

        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_init_overwrites_with_force(self, tmp_path):
        """Test init overwrites existing file with --force."""
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text("existing content")

        result = runner.invoke(
            app,
            ["init", "--force", "--output", str(config_file)],
        )

        assert result.exit_code == 0
        content = config_file.read_text()
        assert "existing content" not in content
        assert "scripts:" in content


class TestValidateCommand:
    """Test the 'lazarus validate' command."""

    def test_validate_valid_config(self, temp_config_file):
        """Test validate command with valid config."""
        result = runner.invoke(app, ["validate", str(temp_config_file)])

        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_config(self, tmp_path):
        """Test validate command with invalid config."""
        # Create invalid config (missing required fields)
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        result = runner.invoke(app, ["validate", str(config_file)])

        assert result.exit_code != 0

    def test_validate_no_config_found(self, tmp_path):
        """Test validate command when no config is found."""
        # Run from directory without config
        with patch("lazarus.config.loader.find_config_file", return_value=None):
            result = runner.invoke(app, ["validate"])

            assert result.exit_code == 1
            assert "No lazarus.yaml found" in result.stdout

    def test_validate_verbose(self, temp_config_file):
        """Test validate command with verbose flag."""
        result = runner.invoke(
            app,
            ["validate", str(temp_config_file), "--verbose"],
        )

        assert result.exit_code == 0


class TestHealCommand:
    """Test the 'lazarus heal' command."""

    def test_heal_script_not_found(self):
        """Test heal command with non-existent script."""
        result = runner.invoke(app, ["heal", "/nonexistent/script.py"])

        assert result.exit_code != 0

    def test_heal_with_dry_run(self, temp_script, tmp_path):
        """Test heal command with --dry-run flag."""
        # Create a minimal config file
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text(
            """
scripts: []
healing:
  max_attempts: 3
logging:
  level: INFO
  console: true
"""
        )

        result = runner.invoke(
            app,
            ["heal", str(temp_script), "--config", str(config_file), "--dry-run"],
        )

        # Dry run should exit without error but not do anything
        assert "Dry run mode" in result.stdout

    def test_heal_success(self, temp_script, sample_config, tmp_path):
        """Test heal command with successful healing."""
        # Create a config file
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text(
            """
scripts:
  - name: test
    path: test.py
    timeout: 300

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900

logging:
  level: INFO
  console: true
"""
        )

        # Mock the healing process and history manager
        with (
            patch("lazarus.core.healer.Healer.heal") as mock_heal,
            patch("lazarus.logging.history.HealingHistory.record") as mock_history,
        ):
            mock_heal.return_value = Mock(
                success=True,
                attempts=[],
                final_execution=Mock(exit_code=0),
                duration=5.0,
                error_message=None,
            )
            mock_history.return_value = "test-record-id"

            result = runner.invoke(
                app,
                ["heal", str(temp_script), "--config", str(config_file)],
            )

            assert result.exit_code == 0
            assert "Success" in result.stdout

    def test_heal_failure(self, temp_script, tmp_path):
        """Test heal command with failed healing."""
        # Create a config file
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text(
            """
scripts:
  - name: test
    path: test.py
    timeout: 300

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900

logging:
  level: INFO
  console: true
"""
        )

        # Mock the healing process and history manager
        with (
            patch("lazarus.core.healer.Healer.heal") as mock_heal,
            patch("lazarus.logging.history.HealingHistory.record") as mock_history,
        ):
            mock_heal.return_value = Mock(
                success=False,
                attempts=[],
                final_execution=Mock(exit_code=1),
                duration=10.0,
                error_message="Failed to heal",
            )
            mock_history.return_value = "test-record-id"

            result = runner.invoke(
                app,
                ["heal", str(temp_script), "--config", str(config_file)],
            )

            assert result.exit_code == 1
            assert "Failed" in result.stdout

    def test_heal_with_max_attempts_override(self, temp_script, tmp_path):
        """Test heal command with --max-attempts override."""
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text(
            """
scripts: []
healing:
  max_attempts: 3
logging:
  level: INFO
  console: true
"""
        )

        with (
            patch("lazarus.core.healer.Healer.heal") as mock_heal,
            patch("lazarus.logging.history.HealingHistory.record") as mock_history,
        ):
            mock_heal.return_value = Mock(
                success=True,
                attempts=[],
                final_execution=Mock(exit_code=0),
                duration=5.0,
                error_message=None,
            )
            mock_history.return_value = "test-record-id"

            result = runner.invoke(
                app,
                [
                    "heal",
                    str(temp_script),
                    "--config",
                    str(config_file),
                    "--max-attempts",
                    "5",
                ],
            )

            # Verify the heal was called
            assert mock_heal.called


class TestRunCommand:
    """Test the 'lazarus run' command."""

    def test_run_is_alias_for_heal(self, temp_script, tmp_path):
        """Test that run command is an alias for heal."""
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text(
            """
scripts: []
healing:
  max_attempts: 3
logging:
  level: INFO
  console: true
"""
        )

        with (
            patch("lazarus.core.healer.Healer.heal") as mock_heal,
            patch("lazarus.logging.history.HealingHistory.record") as mock_history,
        ):
            mock_heal.return_value = Mock(
                success=True,
                attempts=[],
                final_execution=Mock(exit_code=0),
                duration=5.0,
                error_message=None,
            )
            mock_history.return_value = "test-record-id"

            result = runner.invoke(
                app,
                ["run", str(temp_script), "--config", str(config_file)],
            )

            assert result.exit_code == 0
            assert mock_heal.called


class TestHistoryCommand:
    """Test the 'lazarus history' command."""

    def test_history_no_records(self):
        """Test history command with no healing records."""
        with patch("lazarus.logging.history.HealingHistory.get_history") as mock_get:
            mock_get.return_value = []

            result = runner.invoke(app, ["history"])

            assert result.exit_code == 0
            assert "No healing history" in result.stdout

    def test_history_with_records(self):
        """Test history command with healing records."""
        from lazarus.logging.history import HistoryRecord

        mock_records = [
            HistoryRecord(
                id="test-1",
                timestamp="2024-01-01T12:00:00",
                script_path="/test/script.py",
                success=True,
                attempts_count=1,
                duration=5.0,
                pr_url="https://github.com/test/repo/pull/1",
                error_summary=None,
            ),
        ]

        with patch("lazarus.logging.history.HealingHistory.get_history") as mock_get:
            mock_get.return_value = mock_records

            result = runner.invoke(app, ["history"])

            assert result.exit_code == 0
            assert "script.py" in result.stdout

    def test_history_with_limit(self):
        """Test history command with --limit flag."""
        with patch("lazarus.logging.history.HealingHistory.get_history") as mock_get:
            mock_get.return_value = []

            result = runner.invoke(app, ["history", "--limit", "5"])

            assert result.exit_code == 0
            mock_get.assert_called_once()
            # Verify limit was passed
            assert mock_get.call_args[1]["limit"] == 5

    def test_history_json_output(self):
        """Test history command with --json flag."""
        from lazarus.logging.history import HistoryRecord

        mock_records = [
            HistoryRecord(
                id="test-1",
                timestamp="2024-01-01T12:00:00",
                script_path="/test/script.py",
                success=True,
                attempts_count=1,
                duration=5.0,
                pr_url=None,
                error_summary=None,
            ),
        ]

        with patch("lazarus.logging.history.HealingHistory.get_history") as mock_get:
            mock_get.return_value = mock_records

            result = runner.invoke(app, ["history", "--json"])

            assert result.exit_code == 0
            # Output should be JSON
            assert "{" in result.stdout
            assert "test-1" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_config_error_handling(self, tmp_path):
        """Test handling of configuration errors."""
        # Create the script file
        script_file = tmp_path / "script.py"
        script_file.write_text("print('test')")

        # Create invalid config
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("not: valid: yaml:")

        with patch("lazarus.config.loader.load_config") as mock_load:
            from lazarus.config.loader import ConfigError

            mock_load.side_effect = ConfigError("Invalid config")

            result = runner.invoke(
                app,
                ["heal", str(script_file), "--config", str(config_file)],
            )

            assert result.exit_code == 2
            assert "Configuration error" in result.stdout

    def test_file_not_found_handling(self):
        """Test handling of file not found errors."""
        result = runner.invoke(app, ["heal", "/definitely/does/not/exist.py"])

        assert result.exit_code != 0

    def test_unexpected_error_handling(self, temp_script, tmp_path):
        """Test handling of unexpected errors."""
        config_file = tmp_path / "lazarus.yaml"
        config_file.write_text("scripts: []\nhealing: {}\nlogging: {level: INFO}")

        with patch("lazarus.core.healer.Healer.heal") as mock_heal:
            mock_heal.side_effect = RuntimeError("Unexpected error")

            result = runner.invoke(
                app,
                ["heal", str(temp_script), "--config", str(config_file)],
            )

            assert result.exit_code == 3
            assert "Unexpected error" in result.stdout
