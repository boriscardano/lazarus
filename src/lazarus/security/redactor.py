"""Secrets redaction for sensitive information in execution context.

This module provides functionality to detect and redact sensitive information
like API keys, passwords, tokens, and other secrets from execution context
before it's sent to Claude or logged.
"""

from __future__ import annotations

import re
from dataclasses import replace

from lazarus.config.schema import LazarusConfig
from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
    PreviousAttempt,
    SystemContext,
)


class Redactor:
    """Redacts sensitive information from text using regex patterns.

    This class uses configurable regex patterns to identify and redact
    sensitive information like API keys, passwords, tokens, etc.

    Attributes:
        patterns: List of compiled regex patterns with their names
    """

    def __init__(self, pattern_configs: list[tuple[str, str]]):
        """Initialize redactor with patterns.

        Args:
            pattern_configs: List of (name, pattern) tuples where name is a
                human-readable identifier and pattern is a regex string
        """
        self.patterns: list[tuple[str, re.Pattern[str]]] = [
            (name, re.compile(pattern)) for name, pattern in pattern_configs
        ]

    @classmethod
    def from_config(cls, config: LazarusConfig) -> Redactor:
        """Create a Redactor from Lazarus configuration.

        Args:
            config: Lazarus configuration with security settings

        Returns:
            Configured Redactor instance
        """
        # Combine built-in and additional patterns
        all_patterns = (
            config.security.redact_patterns + config.security.additional_patterns
        )

        # Create pattern configs with names
        pattern_configs: list[tuple[str, str]] = []

        # Default pattern names based on what they detect
        default_names = [
            "api_key",
            "token",
            "secret",
            "password",
            "bearer",
            "authorization",
            "aws_access_key",
            "aws_secret_key",
            "private_key",
            "private_key_block",
        ]

        for i, pattern in enumerate(all_patterns):
            # Use default name if available, otherwise generate one
            name = (
                default_names[i]
                if i < len(default_names)
                else f"custom_pattern_{i - len(default_names) + 1}"
            )
            pattern_configs.append((name, pattern))

        return cls(pattern_configs)

    def redact(self, text: str) -> str:
        """Redact sensitive information from text.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive information replaced by [REDACTED:pattern_name]
        """
        redacted = text

        for name, pattern in self.patterns:
            # Replace all matches with redaction marker
            redacted = pattern.sub(f"[REDACTED:{name}]", redacted)

        return redacted

    def redact_dict(self, data: dict[str, str]) -> dict[str, str]:
        """Redact sensitive information from a dictionary.

        Args:
            data: Dictionary to redact

        Returns:
            New dictionary with redacted values
        """
        return {key: self.redact(value) for key, value in data.items()}


def redact_execution_result(
    result: ExecutionResult, redactor: Redactor
) -> ExecutionResult:
    """Redact sensitive information from execution result.

    Args:
        result: Execution result to redact
        redactor: Redactor instance to use

    Returns:
        New ExecutionResult with redacted stdout and stderr
    """
    return replace(
        result,
        stdout=redactor.redact(result.stdout),
        stderr=redactor.redact(result.stderr),
    )


def redact_commit_info(commit: CommitInfo, redactor: Redactor) -> CommitInfo:
    """Redact sensitive information from commit info.

    Args:
        commit: Commit info to redact
        redactor: Redactor instance to use

    Returns:
        New CommitInfo with redacted message and diff
    """
    return replace(
        commit,
        message=redactor.redact(commit.message),
        diff=redactor.redact(commit.diff) if commit.diff else None,
    )


def redact_git_context(
    git_context: GitContext | None, redactor: Redactor
) -> GitContext | None:
    """Redact sensitive information from git context.

    Args:
        git_context: Git context to redact (can be None)
        redactor: Redactor instance to use

    Returns:
        New GitContext with redacted commits and changes, or None if input was None
    """
    if git_context is None:
        return None

    return replace(
        git_context,
        recent_commits=[
            redact_commit_info(commit, redactor)
            for commit in git_context.recent_commits
        ],
        uncommitted_changes=redactor.redact(git_context.uncommitted_changes),
    )


def redact_system_context(
    system_context: SystemContext, redactor: Redactor
) -> SystemContext:
    """Redact sensitive information from system context.

    Currently, system context doesn't contain user-controlled data that would
    typically contain secrets, but we redact the shell path just in case.

    Args:
        system_context: System context to redact
        redactor: Redactor instance to use

    Returns:
        New SystemContext with redacted fields
    """
    return replace(
        system_context,
        shell=redactor.redact(system_context.shell),
    )


def redact_previous_attempt(
    attempt: PreviousAttempt, redactor: Redactor
) -> PreviousAttempt:
    """Redact sensitive information from a previous healing attempt.

    The error_after field can contain secrets from stdout/stderr of failed
    attempts, so we need to redact it to prevent secret leakage.

    Args:
        attempt: Previous attempt to redact
        redactor: Redactor instance to use

    Returns:
        New PreviousAttempt with redacted error_after and claude_response_summary
    """
    return replace(
        attempt,
        error_after=redactor.redact(attempt.error_after),
        claude_response_summary=redactor.redact(attempt.claude_response_summary),
    )


def redact_context(context: HealingContext) -> HealingContext:
    """Redact sensitive information from complete healing context.

    This is the main function to use for redacting all sensitive information
    from a HealingContext before sending it to Claude or logging it.

    Args:
        context: Healing context to redact

    Returns:
        New HealingContext with all sensitive information redacted
    """
    # Create redactor from config
    redactor = Redactor.from_config(context.config)

    # Redact script content
    redacted_script_content = redactor.redact(context.script_content)

    # Redact execution result
    redacted_execution_result = redact_execution_result(
        context.execution_result, redactor
    )

    # Redact git context
    redacted_git_context = redact_git_context(context.git_context, redactor)

    # Redact system context
    redacted_system_context = redact_system_context(context.system_context, redactor)

    # Redact previous attempts
    redacted_previous_attempts = [
        redact_previous_attempt(attempt, redactor)
        for attempt in context.previous_attempts
    ]

    # Create new context with redacted data
    return replace(
        context,
        script_content=redacted_script_content,
        execution_result=redacted_execution_result,
        git_context=redacted_git_context,
        system_context=redacted_system_context,
        previous_attempts=redacted_previous_attempts,
    )


def filter_environment_variables(
    env_vars: dict[str, str], safe_vars: list[str]
) -> dict[str, str]:
    """Filter environment variables to only include safe ones.

    Args:
        env_vars: All environment variables
        safe_vars: List of variable names that are safe to include

    Returns:
        Dictionary containing only safe environment variables
    """
    return {
        key: value for key, value in env_vars.items() if key in safe_vars
    }
