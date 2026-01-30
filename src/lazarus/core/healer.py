"""Main healing orchestrator - the heart of Lazarus.

This module provides the core Healer class that orchestrates the entire healing
process: running scripts, capturing failures, calling Claude Code for fixes,
verifying fixes, and managing the retry loop.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lazarus.claude.client import ClaudeCodeClient
from lazarus.claude.parser import ClaudeResponse
from lazarus.config.schema import LazarusConfig, ScriptConfig
from lazarus.core.context import (
    ExecutionResult,
    HealingContext,
    PreviousAttempt,
    build_context,
)
from lazarus.core.loop import HealingLoop
from lazarus.core.runner import ScriptRunner
from lazarus.core.verification import VerificationResult
from lazarus.git.operations import GitOperationError, GitOperations
from lazarus.git.pr import PRCreator
from lazarus.security.redactor import redact_context

logger = logging.getLogger(__name__)


@dataclass
class HealingAttempt:
    """Record of a single healing attempt.

    Attributes:
        attempt_number: Attempt number (1-indexed)
        claude_response: Response from Claude Code
        verification: Result of verifying the fix
        duration: Time taken for this attempt in seconds
    """

    attempt_number: int
    claude_response: ClaudeResponse
    verification: VerificationResult
    duration: float


@dataclass
class HealingResult:
    """Complete result of the healing process.

    Attributes:
        success: Whether healing was ultimately successful
        attempts: List of all healing attempts made
        final_execution: Final execution result (after last attempt)
        pr_url: URL of created pull request (if applicable)
        duration: Total duration of healing process in seconds
        error_message: Error message if healing failed
    """

    success: bool
    attempts: list[HealingAttempt]
    final_execution: ExecutionResult
    pr_url: str | None = None
    duration: float = 0.0
    error_message: str | None = None


class Healer:
    """Main orchestrator for the healing process.

    This is the heart of Lazarus. It coordinates all the components to:
    1. Run a script and capture any failure
    2. Build comprehensive context with redaction
    3. Loop through healing attempts using Claude Code
    4. Verify each fix by re-running the script
    5. Return a complete healing result

    Attributes:
        config: Lazarus configuration
        runner: Script runner for executing and verifying scripts
        loop: Healing loop manager for retry logic
    """

    def __init__(self, config: LazarusConfig, repo_path: Path | None = None) -> None:
        """Initialize the healer.

        Args:
            config: Lazarus configuration object
            repo_path: Path to git repository root (optional, will be detected)
        """
        self.config = config
        self.runner = ScriptRunner(config)
        self.loop = HealingLoop(
            max_attempts=config.healing.max_attempts,
            timeout_per_attempt=config.healing.timeout_per_attempt,
            total_timeout=config.healing.total_timeout,
        )

        # Initialize git operations if in a git repo
        self.git_ops: GitOperations | None = None
        if repo_path:
            try:
                self.git_ops = GitOperations(repo_path)
            except ValueError:
                logger.warning("Not a git repository: %s", repo_path)
        else:
            # Try to detect git repo from current directory
            try:
                self.git_ops = GitOperations(Path.cwd())
            except ValueError:
                logger.debug("Not in a git repository")

    def heal(self, script_path: Path) -> HealingResult:
        """Heal a failing script with integrated git workflow.

        This orchestrates:
        1. Stashing uncommitted changes
        2. Creating a feature branch
        3. Running the healing process
        4. Pushing changes and creating a PR
        5. Returning to original branch and restoring stashed changes

        Args:
            script_path: Path to the script to heal

        Returns:
            HealingResult with PR URL if applicable

        Raises:
            FileNotFoundError: If script_path does not exist
        """
        start_time = time.time()

        # Validate script exists
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Git workflow state tracking
        original_branch: str | None = None
        stashed_changes = False
        feature_branch: str | None = None

        try:
            # === GIT SETUP PHASE ===
            # Step 1: Stash uncommitted changes if present
            if self.git_ops and self.git_ops.has_uncommitted_changes():
                logger.info("Uncommitted changes detected, stashing...")
                try:
                    self.git_ops.stash_changes("Lazarus: auto-stash before healing")
                    stashed_changes = True
                    logger.info("Changes stashed successfully")
                except GitOperationError as e:
                    logger.warning("Failed to stash changes: %s", e)
                    # Continue - not fatal

            # Step 2: Create and checkout feature branch
            if self.git_ops:
                try:
                    original_branch = self.git_ops.get_current_branch()
                    feature_branch = self._generate_branch_name(script_path)

                    logger.info("Creating feature branch: %s", feature_branch)
                    if self.git_ops.branch_exists(feature_branch):
                        logger.info("Branch already exists, checking out")
                        self.git_ops.checkout_branch(feature_branch)
                    else:
                        self.git_ops.create_and_checkout_branch(feature_branch)
                    logger.info("Now on branch: %s", feature_branch)
                except GitOperationError as e:
                    logger.warning("Failed to create/checkout feature branch: %s", e)
                    # Continue - healing can work without git

            # === HEALING PHASE ===
            # Find script configuration
            script_config = self._find_script_config(script_path)

            # Run initial execution
            initial_result = self._run_script(script_path, script_config)

            # If script succeeds on first run, no healing needed
            if initial_result.success:
                duration = time.time() - start_time
                result = HealingResult(
                    success=True,
                    attempts=[],
                    final_execution=initial_result,
                    duration=duration,
                    error_message=None,
                )
                # Clean up and return (no changes were made)
                return self._finalize_healing(
                    result=result,
                    script_path=script_path,
                    original_branch=original_branch,
                    stashed_changes=stashed_changes,
                    feature_branch=feature_branch,
                    has_changes=False,
                )

            # Build context for healing
            context = build_context(
                script_path=script_path,
                result=initial_result,
                config=self.config,
            )

            # SECURITY: Redact secrets before sending to Claude
            context = redact_context(context)

            # Initialize Claude Code client
            working_dir = (
                script_config.working_dir
                if script_config and script_config.working_dir
                else script_path.parent
            )
            claude_client = ClaudeCodeClient(
                working_dir=working_dir,
                timeout=self.config.healing.timeout_per_attempt,
            )

            # Check if Claude Code is available
            if not claude_client.is_available():
                duration = time.time() - start_time
                result = HealingResult(
                    success=False,
                    attempts=[],
                    final_execution=initial_result,
                    duration=duration,
                    error_message=(
                        "Claude Code CLI is not available. Please install it:\n"
                        "  npm install -g @anthropic-ai/claude-code"
                    ),
                )
                return self._finalize_healing(
                    result=result,
                    script_path=script_path,
                    original_branch=original_branch,
                    stashed_changes=stashed_changes,
                    feature_branch=feature_branch,
                    has_changes=False,
                )

            # Healing loop
            attempts: list[HealingAttempt] = []
            current_execution = initial_result

            for attempt_number in self.loop:
                attempt_start = time.time()

                # Request fix from Claude Code
                claude_response = claude_client.request_fix(context)

                # Verify the fix by re-running the script
                verification = self.runner.verify_fix(
                    script_path=script_path,
                    previous_result=current_execution,
                    config=script_config,
                )

                attempt_duration = time.time() - attempt_start

                # Record this attempt
                attempt = HealingAttempt(
                    attempt_number=attempt_number,
                    claude_response=claude_response,
                    verification=verification,
                    duration=attempt_duration,
                )
                attempts.append(attempt)

                # Update current execution for next iteration
                current_execution = verification.execution_result

                # Check if healing succeeded
                if verification.status == "success":
                    self.loop.mark_success()
                    break

                # Update context based on result
                if verification.status == "same_error":
                    context = self._enhance_context_for_retry(
                        context=context,
                        attempt=attempt,
                        attempt_number=attempt_number,
                    )
                elif verification.status == "different_error":
                    previous_attempt = PreviousAttempt(
                        attempt_number=attempt.attempt_number,
                        claude_response_summary=(
                            attempt.claude_response.explanation or "Unknown fix attempt"
                        ),
                        changes_made=attempt.claude_response.files_changed or [],
                        error_after=(
                            attempt.verification.execution_result.stderr
                            or attempt.verification.execution_result.stdout
                            or f"Exit code: {attempt.verification.execution_result.exit_code}"
                        ),
                    )
                    new_context = build_context(
                        script_path=script_path,
                        result=verification.execution_result,
                        config=self.config,
                    )
                    new_context.previous_attempts = context.previous_attempts + [
                        previous_attempt
                    ]
                    # SECURITY: Redact secrets in new context
                    context = redact_context(new_context)
                elif verification.status == "timeout":
                    context = self._enhance_context_for_retry(
                        context=context,
                        attempt=attempt,
                        attempt_number=attempt_number,
                    )

            # === FINALIZATION PHASE ===
            # Determine overall success
            total_duration = time.time() - start_time
            final_success = bool(attempts and attempts[-1].verification.status == "success")

            # Prepare error message if failed
            error_message = None
            if not final_success:
                if not attempts:
                    error_message = "No healing attempts were made"
                elif attempts[-1].claude_response.error_message:
                    error_message = attempts[-1].claude_response.error_message
                else:
                    error_message = (
                        f"Failed to heal after {len(attempts)} attempts. "
                        f"Final status: {attempts[-1].verification.status}"
                    )

            result = HealingResult(
                success=final_success,
                attempts=attempts,
                final_execution=current_execution,
                pr_url=None,  # Will be set in _finalize_healing
                duration=total_duration,
                error_message=error_message,
            )

            # Finalize with git operations and PR creation
            return self._finalize_healing(
                result=result,
                script_path=script_path,
                original_branch=original_branch,
                stashed_changes=stashed_changes,
                feature_branch=feature_branch,
                has_changes=bool(attempts),  # Changes were made if attempts were made
            )

        except Exception as e:
            # Emergency cleanup if something goes wrong
            logger.error("Emergency cleanup after error: %s", e, exc_info=True)
            if self.git_ops and original_branch:
                try:
                    self.git_ops.checkout_branch(original_branch)
                    if stashed_changes:
                        self.git_ops.pop_stash()
                except GitOperationError as cleanup_error:
                    logger.error("Failed to clean up git state: %s", cleanup_error)
            raise



    def _run_script(
        self,
        script_path: Path,
        config: ScriptConfig | None,
    ) -> ExecutionResult:
        """Run a script with appropriate configuration.

        Args:
            script_path: Path to script
            config: Optional script configuration

        Returns:
            ExecutionResult from running the script
        """
        timeout = config.timeout if config else 300
        working_dir = config.working_dir if config else None

        return self.runner.run_script(
            script_path=script_path,
            working_dir=working_dir,
            timeout=timeout,
        )

    def _find_script_config(self, script_path: Path) -> ScriptConfig | None:
        """Find script configuration for a given script path.

        Args:
            script_path: Path to the script

        Returns:
            ScriptConfig if found, None otherwise
        """
        for script_config in self.config.scripts:
            # Match by name or by path
            if (
                script_config.path.name == script_path.name
                or script_config.path.resolve() == script_path.resolve()
            ):
                return script_config
        return None

    def _has_uncommitted_changes(self, script_path: Path) -> bool:
        """Check if there are uncommitted changes to the script.

        Args:
            script_path: Path to check

        Returns:
            True if there are uncommitted changes
        """
        try:
            # Check git status for this specific file
            result = subprocess.run(
                ["git", "status", "--porcelain", str(script_path)],
                cwd=script_path.parent,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # If there's output, there are uncommitted changes
            return bool(result.stdout.strip())

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            # If git command fails, assume no uncommitted changes
            return False

    def _enhance_context_for_retry(
        self,
        context: HealingContext,
        attempt: HealingAttempt,
        attempt_number: int,
    ) -> HealingContext:
        """Enhance context with information from a failed attempt.

        This creates a new context that includes information about what was
        already tried, helping Claude avoid repeating the same unsuccessful fix.

        Args:
            context: Original healing context
            attempt: The failed attempt
            attempt_number: Attempt number

        Returns:
            Enhanced HealingContext
        """
        # Build a record of this failed attempt
        previous_attempt = PreviousAttempt(
            attempt_number=attempt.attempt_number,
            claude_response_summary=attempt.claude_response.explanation or "Unknown fix attempt",
            changes_made=attempt.claude_response.files_changed or [],
            error_after=(
                attempt.verification.execution_result.stderr
                or attempt.verification.execution_result.stdout
                or f"Exit code: {attempt.verification.execution_result.exit_code}"
            ),
        )

        # Build new context with the latest execution result
        new_context = build_context(
            script_path=context.script_path,
            result=attempt.verification.execution_result,
            config=self.config,
        )

        # Add all previous attempts (including this one)
        new_context.previous_attempts = context.previous_attempts + [previous_attempt]

        # SECURITY: Redact secrets in new context
        return redact_context(new_context)

    def _finalize_healing(
        self,
        result: HealingResult,
        script_path: Path,
        original_branch: str | None,
        stashed_changes: bool,
        feature_branch: str | None,
        has_changes: bool,
    ) -> HealingResult:
        """Finalize the healing process with git operations and notifications.

        This handles:
        - Pushing changes to remote (if any were made)
        - Creating a PR (if healing was successful and config enabled)
        - Returning to original branch
        - Restoring stashed changes
        - Sending notifications

        Args:
            result: The healing result
            script_path: Path to the healed script
            original_branch: Original branch we started on
            stashed_changes: Whether we stashed changes at the start
            feature_branch: Feature branch created for healing
            has_changes: Whether any changes were made during healing

        Returns:
            Updated HealingResult with PR URL if applicable
        """
        # Handle git operations if in a git repo
        if self.git_ops:
            try:
                # Step 1: Push branch to remote if changes were made
                if has_changes and feature_branch and self._has_remote():
                    try:
                        logger.info("Pushing branch %s to remote", feature_branch)
                        self.git_ops.push(
                            remote="origin",
                            branch=feature_branch,
                            set_upstream=True,
                        )
                        logger.info("Branch pushed successfully")
                    except GitOperationError as e:
                        logger.warning("Failed to push branch: %s", e)
                        # Continue - we'll note this in the result

                # Step 2: Create PR if healing was successful and config enabled
                if result.success and has_changes and self.config.git.create_pr:
                    try:
                        logger.info("Creating pull request")
                        pr_creator = PRCreator(
                            config=self.config.git,
                            repo_path=self.git_ops.repo_path,
                        )
                        pr_result = pr_creator.create_pr(
                            healing_result=result,
                            script_path=script_path,
                        )

                        if pr_result.success and pr_result.pr_url:
                            result.pr_url = pr_result.pr_url
                            logger.info("PR created: %s", pr_result.pr_url)
                        else:
                            logger.warning("Failed to create PR: %s", pr_result.error_message)
                    except Exception as e:
                        logger.error("Error creating PR: %s", e, exc_info=True)
                        # Don't fail the healing process if PR creation fails

                # Step 3: Push branch even if healing failed (for debugging)
                elif not result.success and has_changes and feature_branch and self._has_remote():
                    try:
                        logger.info("Pushing failed healing attempt for debugging")
                        self.git_ops.push(
                            remote="origin",
                            branch=feature_branch,
                            set_upstream=True,
                        )
                        logger.info("Failed healing branch pushed for manual review")
                    except GitOperationError as e:
                        logger.warning("Failed to push debugging branch: %s", e)

            finally:
                # Step 4: Always return to original branch
                if original_branch:
                    try:
                        logger.info("Returning to original branch: %s", original_branch)
                        self.git_ops.checkout_branch(original_branch)
                        logger.info("Checked out original branch")
                    except GitOperationError as e:
                        logger.error("Failed to return to original branch: %s", e)
                        # This is a serious problem - warn the user
                        if not result.error_message:
                            result.error_message = f"Failed to return to original branch: {e}"
                        else:
                            result.error_message += f"\nWarning: Failed to return to original branch: {e}"

                # Step 5: Always restore stashed changes
                if stashed_changes:
                    try:
                        logger.info("Restoring stashed changes")
                        self.git_ops.pop_stash()
                        logger.info("Stashed changes restored")
                    except GitOperationError as e:
                        logger.error("Failed to restore stashed changes: %s", e)
                        warning = "Failed to restore stashed changes - use 'git stash pop' manually"
                        if not result.error_message:
                            result.error_message = warning
                        else:
                            result.error_message += f"\nWarning: {warning}"

        # Send notifications if configured
        if self.config.notifications:
            try:
                # Lazy import to avoid circular dependency
                from lazarus.notifications import NotificationDispatcher

                dispatcher = NotificationDispatcher(self.config.notifications)
                dispatcher.dispatch(
                    result=result,
                    script_path=script_path,
                )
                logger.info("Notifications dispatched")
            except Exception as e:
                # Log but don't fail healing due to notification errors
                logger.warning("Failed to send notifications: %s", e)

        return result

    def _generate_branch_name(self, script_path: Path) -> str:
        """Generate a feature branch name for healing.

        Uses the pattern from config.git.branch_prefix and script name.

        Args:
            script_path: Path to the script being healed

        Returns:
            Branch name like "lazarus/fix-backup-20260130-143052"
        """
        # Get script name without extension
        script_name = script_path.stem.replace("_", "-").replace(".", "-").lower()

        # Add timestamp for uniqueness
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

        # Combine with prefix from config
        prefix = self.config.git.branch_prefix
        branch_name = f"{prefix}-{script_name}-{timestamp}"

        return branch_name

    def _has_remote(self) -> bool:
        """Check if the repository has a configured remote.

        Returns:
            True if the repository has an 'origin' remote configured
        """
        if not self.git_ops:
            return False

        try:
            remote_url = self.git_ops.get_remote_url("origin")
            return remote_url is not None
        except GitOperationError:
            return False

