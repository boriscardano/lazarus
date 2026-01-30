"""GitHub Issues notification channel implementation.

This module provides GitHub Issues notifications using the gh CLI tool.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from lazarus.config.schema import GitHubIssuesConfig
from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


class GitHubIssueNotifier:
    """GitHub Issues notification channel using gh CLI.

    Creates GitHub issues for healing failures with error details and labels.
    Only creates issues on failure by default (configurable).

    Attributes:
        config: GitHub Issues configuration including repo and labels
        timeout: Command execution timeout in seconds (default: 30)
    """

    def __init__(self, config: GitHubIssuesConfig, timeout: int = 30) -> None:
        """Initialize GitHub Issue notifier.

        Args:
            config: GitHub Issues configuration
            timeout: Command execution timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._name = "github_issues"

    @property
    def name(self) -> str:
        """Get the name of this notification channel."""
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Create a GitHub issue about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if issue was created successfully, False otherwise
        """
        # Only create issues on failure (unless configured otherwise)
        if result.success:
            logger.debug("Skipping GitHub issue creation for successful healing")
            return True

        if not result.success and not self.config.on_failure:
            logger.debug("Skipping GitHub issue creation for failed healing (disabled)")
            return True

        try:
            # Check if gh CLI is available
            if not self._is_gh_available():
                logger.error("gh CLI is not available. Please install it: https://cli.github.com/")
                return False

            # Build issue title and body
            title = self._build_title(script_path)
            body = self._build_body(result, script_path)

            # Create issue using gh CLI
            cmd = [
                "gh", "issue", "create",
                "--repo", self.config.repo,
                "--title", title,
                "--body", body,
            ]

            # Add labels
            for label in self.config.labels:
                cmd.extend(["--label", label])

            # Add assignees if specified
            for assignee in self.config.assignees:
                cmd.extend(["--assignee", assignee])

            result_proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result_proc.returncode != 0:
                logger.error(f"Failed to create GitHub issue: {result_proc.stderr}")
                return False

            # Extract issue URL from output
            issue_url = result_proc.stdout.strip()
            logger.info(f"Successfully created GitHub issue: {issue_url}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout while creating GitHub issue")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating GitHub issue: {e}")
            return False

    def _is_gh_available(self) -> bool:
        """Check if gh CLI is available.

        Returns:
            True if gh CLI is available and authenticated
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _build_title(self, script_path: Path) -> str:
        """Build issue title.

        Args:
            script_path: Path to script

        Returns:
            Issue title
        """
        return f"[Lazarus] Healing failed for {script_path.name}"

    def _build_body(self, result: HealingResult, script_path: Path) -> str:
        """Build issue body with error details.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            Issue body in Markdown format
        """
        lines = [
            "## Healing Failed",
            "",
            "Lazarus attempted to heal a script failure but was unsuccessful.",
            "",
            "### Details",
            "",
            f"- **Script**: `{script_path}`",
            f"- **Attempts**: {len(result.attempts)}",
            f"- **Duration**: {result.duration:.2f} seconds",
            f"- **Exit Code**: {result.final_execution.exit_code}",
            f"- **Timestamp**: {result.final_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
        ]

        if result.pr_url:
            lines.extend([
                "### Pull Request",
                "",
                f"A pull request with attempted fixes is available: {result.pr_url}",
                "",
            ])

        if result.error_message:
            lines.extend([
                "### Error Summary",
                "",
                "```",
                result.error_message,
                "```",
                "",
            ])

        if result.final_execution.stderr:
            stderr = result.final_execution.stderr
            # Truncate very long error output
            if len(stderr) > 1000:
                stderr = stderr[:1000] + "\n... (truncated)"

            lines.extend([
                "### Error Output",
                "",
                "```",
                stderr,
                "```",
                "",
            ])

        if result.final_execution.stdout:
            stdout = result.final_execution.stdout
            # Truncate very long output
            if len(stdout) > 1000:
                stdout = stdout[:1000] + "\n... (truncated)"

            lines.extend([
                "<details>",
                "<summary>Standard Output</summary>",
                "",
                "```",
                stdout,
                "```",
                "",
                "</details>",
                "",
            ])

        lines.extend([
            "### Healing Attempts",
            "",
        ])

        for attempt in result.attempts:
            status = "✅" if attempt.verification.status == "success" else "❌"
            lines.extend([
                f"**Attempt {attempt.attempt_number}**: {status} {attempt.verification.status}",
                f"- Duration: {attempt.duration:.2f}s",
                "",
            ])

        lines.extend([
            "---",
            "",
            "*This issue was automatically created by Lazarus.*",
        ])

        return "\n".join(lines)
