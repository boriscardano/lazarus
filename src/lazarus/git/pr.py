"""Pull request creation via GitHub CLI.

This module provides the PRCreator class that orchestrates PR creation
using the gh CLI tool. It handles branch creation, pushing changes,
and creating well-formatted pull requests with comprehensive descriptions.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from lazarus.config.schema import GitConfig
from lazarus.git.operations import GitOperations

if TYPE_CHECKING:
    from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


@dataclass
class PRResult:
    """Result of creating a pull request.

    Attributes:
        success: Whether PR creation was successful
        pr_url: URL of the created pull request (if successful)
        pr_number: PR number (if successful)
        error_message: Error message if creation failed
    """

    success: bool
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    error_message: Optional[str] = None


class PRCreator:
    """Create pull requests via GitHub CLI for healing results.

    This class orchestrates the entire PR creation process:
    1. Create a feature branch
    2. Push changes to remote
    3. Create a PR with formatted title and body
    4. Handle edge cases (existing PRs, authentication issues, etc.)

    Attributes:
        config: Git configuration from Lazarus config
        repo_path: Path to the git repository
        git_ops: GitOperations instance for git commands
    """

    def __init__(self, config: GitConfig, repo_path: Path) -> None:
        """Initialize PRCreator.

        Args:
            config: Git configuration
            repo_path: Path to git repository root
        """
        self.config = config
        self.repo_path = repo_path
        self.git_ops = GitOperations(repo_path)

    def create_pr(
        self,
        healing_result: "HealingResult",
        script_path: Path,
    ) -> PRResult:
        """Create a pull request for healing changes.

        This is the main entry point for PR creation. It orchestrates
        all steps needed to create a PR from healing results.

        Args:
            healing_result: Result from the healing process
            script_path: Path to the script that was healed

        Returns:
            PRResult with PR information or error details
        """
        logger.info("Creating PR for healed script: %s", script_path)

        # Check prerequisites
        if not self.is_gh_available():
            return PRResult(
                success=False,
                error_message=(
                    "GitHub CLI (gh) is not installed. "
                    "Install it from https://cli.github.com/"
                ),
            )

        if not self.is_gh_authenticated():
            return PRResult(
                success=False,
                error_message=(
                    "GitHub CLI is not authenticated. "
                    "Run: gh auth login"
                ),
            )

        # Check if healing was successful
        if not healing_result.success:
            logger.warning("Cannot create PR for failed healing attempt")
            return PRResult(
                success=False,
                error_message="Healing was not successful",
            )

        try:
            # Generate branch name
            branch_name = self._generate_branch_name(script_path)
            logger.info("Using branch name: %s", branch_name)

            # Get current branch and default branch
            original_branch = self.git_ops.get_current_branch()
            default_branch = self.git_ops.get_default_branch()

            # Check if we need to create a new branch
            if original_branch == default_branch:
                # We're on the default branch, need to create feature branch
                logger.info("Creating feature branch from %s", default_branch)

                if self.git_ops.branch_exists(branch_name):
                    # Branch already exists, check for existing PR
                    existing_pr = self.check_existing_pr(branch_name)
                    if existing_pr:
                        logger.info("PR already exists: %s", existing_pr)
                        return PRResult(
                            success=True,
                            pr_url=existing_pr,
                            error_message="PR already exists for this branch",
                        )

                    # Branch exists but no PR, checkout and use it
                    self.git_ops.checkout_branch(branch_name)
                else:
                    # Create new branch
                    self.git_ops.create_and_checkout_branch(branch_name)
            else:
                # Already on a feature branch, use it
                branch_name = original_branch
                logger.info("Using existing branch: %s", branch_name)

            # Check for existing PR on this branch
            existing_pr = self.check_existing_pr(branch_name)
            if existing_pr:
                logger.info("PR already exists: %s", existing_pr)
                return PRResult(
                    success=True,
                    pr_url=existing_pr,
                    error_message="PR already exists for this branch",
                )

            # Push changes to remote
            logger.info("Pushing changes to remote")
            self.git_ops.push(
                remote="origin",
                branch=branch_name,
                set_upstream=True,
            )

            # Create the PR
            pr_title = self.build_pr_title(script_path)
            pr_body = self.build_pr_body(healing_result, script_path)

            logger.info("Creating pull request")
            logger.debug("PR title: %s", pr_title)

            pr_url, pr_number = self._create_pr_via_gh(
                title=pr_title,
                body=pr_body,
                base=default_branch,
                draft=self.config.draft_pr,
            )

            logger.info("PR created successfully: %s", pr_url)

            return PRResult(
                success=True,
                pr_url=pr_url,
                pr_number=pr_number,
            )

        except Exception as e:
            logger.error("Failed to create PR: %s", e, exc_info=True)
            return PRResult(
                success=False,
                error_message=f"Failed to create PR: {e}",
            )

    def build_pr_title(self, script_path: Path) -> str:
        """Build PR title from script path.

        Args:
            script_path: Path to the healed script

        Returns:
            Formatted PR title
        """
        # Use template if configured
        if self.config.pr_title_template:
            return self.config.pr_title_template.format(
                script_name=script_path.name,
                script_path=script_path,
            )

        # Default format: "fix(lazarus): heal scripts/backup.py"
        return f"fix(lazarus): heal {script_path.name}"

    def build_pr_body(
        self,
        healing_result: "HealingResult",
        script_path: Path,
    ) -> str:
        """Build comprehensive PR body with healing details.

        Args:
            healing_result: Result from healing process
            script_path: Path to healed script

        Returns:
            Formatted PR body in Markdown
        """
        # Use template if configured
        if self.config.pr_body_template:
            return self.config.pr_body_template.format(
                script_path=script_path,
                attempts=len(healing_result.attempts),
                duration=healing_result.duration,
            )

        # Build default PR body
        lines = [
            "## Summary",
            "",
            f"Lazarus automatically healed `{script_path.name}` after detecting a failure.",
            "",
            "### Healing Details",
            "",
            f"- **Script**: `{script_path}`",
            f"- **Attempts**: {len(healing_result.attempts)}",
            f"- **Duration**: {healing_result.duration:.2f}s",
            f"- **Status**: {'✅ Success' if healing_result.success else '❌ Failed'}",
            "",
        ]

        # Add error information (redacted)
        if healing_result.attempts:
            first_attempt = healing_result.attempts[0]
            initial_error = first_attempt.verification.execution_result.stderr

            if initial_error:
                lines.extend([
                    "### Original Error",
                    "",
                    "```",
                    self._redact_sensitive_info(initial_error[:500]),
                    "```",
                    "",
                ])

        # Add changes summary
        lines.extend([
            "### Changes Made",
            "",
            "Claude Code analyzed the error and made the following changes:",
            "",
        ])

        # List attempts
        for attempt in healing_result.attempts:
            lines.append(
                f"**Attempt {attempt.attempt_number}**: "
                f"{attempt.verification.status}"
            )

        lines.extend([
            "",
            "### Test Instructions",
            "",
            "To verify this fix:",
            "",
            "1. Checkout this branch",
            f"2. Run the script: `{script_path}`",
            "3. Verify it completes successfully",
            "",
            "---",
            "",
            "🤖 *This PR was automatically generated by [Lazarus](https://github.com/yourusername/lazarus) "
            "using Claude Code*",
        ])

        return "\n".join(lines)

    def check_existing_pr(self, branch: str) -> Optional[str]:
        """Check if a PR already exists for the given branch.

        Args:
            branch: Branch name to check

        Returns:
            PR URL if exists, None otherwise
        """
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch,
                    "--json",
                    "url,number",
                    "--jq",
                    ".[0].url",
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                pr_url = result.stdout.strip()
                logger.debug("Found existing PR: %s", pr_url)
                return pr_url

            return None

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.warning("Failed to check for existing PR: %s", e)
            return None

    def is_gh_available(self) -> bool:
        """Check if GitHub CLI is available.

        Returns:
            True if gh command is available
        """
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            available = result.returncode == 0
            logger.debug("GitHub CLI available: %s", available)
            return available

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            logger.debug("GitHub CLI not available")
            return False

    def is_gh_authenticated(self) -> bool:
        """Check if GitHub CLI is authenticated.

        Returns:
            True if authenticated with GitHub
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            authenticated = result.returncode == 0
            logger.debug("GitHub CLI authenticated: %s", authenticated)
            return authenticated

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            logger.debug("Failed to check GitHub CLI authentication")
            return False

    def _generate_branch_name(self, script_path: Path) -> str:
        """Generate a branch name from script path.

        Args:
            script_path: Path to the script

        Returns:
            Branch name with configured prefix
        """
        # Get script name without extension
        script_name = script_path.stem

        # Sanitize for branch name - only allow alphanumeric and dashes
        # This prevents command injection via special characters like $, `, |, etc.
        sanitized = re.sub(r'[^a-z0-9-]', '-', script_name.lower())

        # Collapse multiple consecutive dashes into one
        sanitized = re.sub(r'-+', '-', sanitized)

        # Strip leading/trailing dashes
        sanitized = sanitized.strip('-')

        # Ensure the sanitized name is not empty
        if not sanitized:
            sanitized = 'unnamed-script'

        # Combine with prefix
        branch_name = f"{self.config.branch_prefix}/{sanitized}"

        return branch_name

    def _create_pr_via_gh(
        self,
        title: str,
        body: str,
        base: str,
        draft: bool = False,
    ) -> tuple[str, int]:
        """Create a PR using gh CLI.

        Args:
            title: PR title
            body: PR body (markdown)
            base: Base branch to merge into
            draft: Whether to create as draft PR

        Returns:
            Tuple of (PR URL, PR number)

        Raises:
            subprocess.CalledProcessError: If gh command fails
        """
        cmd = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
        ]

        if draft:
            cmd.append("--draft")

        # Add labels if configured
        if hasattr(self.config, "labels") and self.config.labels:
            for label in self.config.labels:
                cmd.extend(["--label", label])

        # Add assignees if configured
        if hasattr(self.config, "assignees") and self.config.assignees:
            for assignee in self.config.assignees:
                cmd.extend(["--assignee", assignee])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )

            # Parse PR URL from output
            pr_url = result.stdout.strip()

            # Extract PR number from URL
            # URL format: https://github.com/owner/repo/pull/123
            pr_number = int(pr_url.split("/")[-1])

            logger.info("Created PR #%d: %s", pr_number, pr_url)

            return pr_url, pr_number

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error"
            logger.error("Failed to create PR: %s", error_msg)
            raise RuntimeError(f"Failed to create PR: {error_msg}") from e

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.error("Failed to execute gh command: %s", e)
            raise RuntimeError(f"Failed to execute gh command: {e}") from e

    def _redact_sensitive_info(self, text: str) -> str:
        """Redact sensitive information from text.

        This is a simple redaction for PR bodies. The full redaction
        logic is in the security module.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive info replaced
        """
        import re

        # Redact common sensitive patterns
        patterns = [
            (r"(['\"]?)([A-Za-z0-9_-]{20,})(['\"]?)", r"\1***REDACTED***\3"),  # API keys
            (r"password[=:]\s*\S+", "password=***REDACTED***"),
            (r"token[=:]\s*\S+", "token=***REDACTED***"),
        ]

        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result
