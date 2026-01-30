"""Claude Code CLI client for script healing.

This module provides a client wrapper around the Claude Code CLI tool,
enabling automated healing of failed scripts through subprocess calls.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from lazarus.claude.parser import ClaudeResponse, parse_claude_output
from lazarus.claude.prompts import build_healing_prompt, build_diagnosis_prompt
from lazarus.core.context import HealingContext


class ClaudeCodeClient:
    """Client for interacting with Claude Code CLI.

    This class wraps the `claude` CLI command to request automated fixes
    for failing scripts. It handles subprocess management, timeouts, and
    error handling.

    Attributes:
        working_dir: Directory to run Claude Code commands from
        timeout: Maximum time to wait for Claude Code response (seconds)
    """

    def __init__(self, working_dir: Path, timeout: int = 300):
        """Initialize the Claude Code client.

        Args:
            working_dir: Directory to run Claude Code commands from
            timeout: Maximum time to wait for Claude Code response (default: 300s)

        Raises:
            ValueError: If working_dir does not exist or is not a directory
        """
        if not working_dir.exists():
            raise ValueError(f"Working directory does not exist: {working_dir}")
        if not working_dir.is_dir():
            raise ValueError(f"Working directory is not a directory: {working_dir}")

        self.working_dir = working_dir.resolve()
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if the claude CLI command is available.

        Returns:
            True if claude CLI is installed and accessible, False otherwise
        """
        return shutil.which("claude") is not None

    def get_version(self) -> Optional[str]:
        """Get the version of the installed Claude Code CLI.

        Returns:
            Version string if available, None if claude is not installed or
            version cannot be determined
        """
        if not self.is_available():
            return None

        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.working_dir,
            )

            if result.returncode == 0:
                # Parse version from output like "claude 1.2.3" or just "1.2.3"
                version_line = result.stdout.strip()
                # Extract version number (major.minor.patch format)
                match = re.search(r'(\d+\.\d+\.\d+)', version_line)
                if match:
                    return match.group(1)
                return version_line

            return None

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            return None

    def request_fix(self, context: HealingContext) -> ClaudeResponse:
        """Request Claude Code to fix a failed script.

        This method:
        1. Builds a structured healing prompt from the context
        2. Calls Claude Code CLI with appropriate flags and constraints
        3. Captures and parses the output
        4. Returns a structured response with the results

        Args:
            context: Complete healing context with error information

        Returns:
            ClaudeResponse with the results of the healing attempt

        Raises:
            RuntimeError: If Claude CLI is not available
            subprocess.TimeoutExpired: If the command exceeds the timeout
        """
        if not self.is_available():
            raise RuntimeError(
                "Claude Code CLI is not available. Please install it first:\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate with:\n"
                "  claude login"
            )

        # Build the healing prompt
        prompt = build_healing_prompt(context)

        # Determine allowed tools based on config
        allowed_tools = self._get_allowed_tools(context)

        # Build the command
        # Use -p flag for prompt-only mode (non-interactive)
        command = [
            "claude",
            "-p",
            prompt,
        ]

        # Add allowed tools constraint if specified
        if allowed_tools:
            command.extend(["--allowedTools", ",".join(allowed_tools)])

        try:
            # Execute Claude Code
            result = subprocess.run(
                command,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Parse the output
            return parse_claude_output(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired as e:
            # Handle timeout
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""

            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"Claude Code timed out after {self.timeout} seconds",
                raw_output=f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
            )

        except subprocess.SubprocessError as e:
            # Handle other subprocess errors
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"Subprocess error: {str(e)}",
                raw_output=str(e),
            )

        except OSError as e:
            # Handle OS errors (e.g., command not found despite is_available check)
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"OS error executing Claude Code: {str(e)}",
                raw_output=str(e),
            )

    def _get_allowed_tools(self, context: HealingContext) -> list[str]:
        """Determine which tools Claude Code should be allowed to use.

        This method examines the healing configuration to build a list of
        allowed tools. For script healing, we typically want:
        - Edit: To modify existing files
        - Write: To create new files (rarely needed)
        - Read: To examine related files
        - Bash: To test changes (optional, depends on config)

        Args:
            context: Healing context with configuration

        Returns:
            List of allowed tool names, or empty list for no restrictions
        """
        # Start with core tools needed for fixing scripts
        default_tools = ["Edit", "Write", "Read"]

        # Check if config specifies allowed tools
        if context.config.healing.allowed_tools:
            # Use explicitly configured tools
            return context.config.healing.allowed_tools

        # Check if there are forbidden tools
        if context.config.healing.forbidden_tools:
            # Remove forbidden tools from defaults
            return [
                tool for tool in default_tools
                if tool not in context.config.healing.forbidden_tools
            ]

        # For focused healing, we typically want to restrict to editing tools only
        # Adding Bash might allow Claude to run tests, which could be useful
        # but also increases risk. Default to safe set.
        return default_tools

    def request_diagnosis(self, context: HealingContext) -> ClaudeResponse:
        """Request Claude Code to diagnose a script failure without making changes.

        This method:
        1. Builds a diagnosis-only prompt from the context
        2. Calls Claude Code CLI with restricted tools to prevent modifications
        3. Captures and parses the diagnostic output
        4. Returns a structured response with the diagnosis

        The diagnosis prompt explicitly instructs Claude not to modify files,
        and we only allow Read tools to ensure no changes are made.

        Args:
            context: Complete healing context with error information

        Returns:
            ClaudeResponse with the diagnostic analysis

        Raises:
            RuntimeError: If Claude CLI is not available
            subprocess.TimeoutExpired: If the command exceeds the timeout
        """
        if not self.is_available():
            raise RuntimeError(
                "Claude Code CLI is not available. Please install it first:\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate with:\n"
                "  claude login"
            )

        # Build the diagnosis prompt
        prompt = build_diagnosis_prompt(context)

        # Build the command with restricted tools for diagnosis only
        # Only allow Read tool to prevent any file modifications
        command = [
            "claude",
            "-p",
            prompt,
            "--allowedTools",
            "Read",  # Only allow reading files, no editing or writing
        ]

        try:
            # Execute Claude Code
            result = subprocess.run(
                command,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Parse the output
            return parse_claude_output(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired as e:
            # Handle timeout
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""

            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"Claude Code timed out after {self.timeout} seconds",
                raw_output=f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
            )

        except subprocess.SubprocessError as e:
            # Handle other subprocess errors
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"Subprocess error: {str(e)}",
                raw_output=str(e),
            )

        except OSError as e:
            # Handle OS errors (e.g., command not found despite is_available check)
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message=f"OS error executing Claude Code: {str(e)}",
                raw_output=str(e),
            )

    def request_fix_with_retry(
        self,
        context: HealingContext,
        max_attempts: Optional[int] = None,
    ) -> tuple[ClaudeResponse, int]:
        """Request a fix with automatic retry on failure.

        This method will attempt healing multiple times if the first attempt
        fails, using information from previous attempts to inform retry prompts.

        Args:
            context: Complete healing context
            max_attempts: Maximum number of attempts (uses config if not specified)

        Returns:
            Tuple of (final ClaudeResponse, number of attempts made)
        """
        if max_attempts is None:
            max_attempts = context.config.healing.max_attempts

        for attempt in range(1, max_attempts + 1):
            response = self.request_fix(context)

            # If successful or this is the last attempt, return
            if response.success or attempt == max_attempts:
                return response, attempt

            # For retry attempts, previous attempt context is handled via
            # the HealingContext.previous_attempts field which is populated
            # by the healer before calling this method again.

        # This should never be reached, but satisfy type checker
        return response, max_attempts
