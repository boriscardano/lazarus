"""Intelligent truncation of context to fit within token limits.

This module provides functionality to truncate healing context to fit within
LLM token limits while preserving the most important information for debugging
and healing.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple heuristic: approximately 4 characters per token.
    This is a rough estimate but good enough for our purposes.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(text) // 4


def truncate_text(
    text: str,
    max_tokens: int,
    position: str = "middle",
) -> str:
    """Truncate text to fit within token limit.

    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        position: Where to truncate - "start", "middle", or "end"

    Returns:
        Truncated text with marker indicating truncation
    """
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    # Calculate how many characters we can keep
    max_chars = max_tokens * 4
    lines = text.split("\n")
    removed_lines = 0

    if position == "start":
        # Remove from the beginning
        chars_count = 0
        for i in range(len(lines) - 1, -1, -1):
            chars_count += len(lines[i]) + 1  # +1 for newline
            if chars_count > max_chars:
                removed_lines = i + 1
                break

        if removed_lines > 0:
            return (
                f"[TRUNCATED: {removed_lines} lines removed from start]\n"
                + "\n".join(lines[removed_lines:])
            )

    elif position == "end":
        # Remove from the end
        chars_count = 0
        for i in range(len(lines)):
            chars_count += len(lines[i]) + 1
            if chars_count > max_chars:
                removed_lines = len(lines) - i
                break

        if removed_lines > 0:
            return (
                "\n".join(lines[:-removed_lines])
                + f"\n[TRUNCATED: {removed_lines} lines removed from end]"
            )

    else:  # middle
        # Keep beginning and end, remove from middle
        target_chars = max_chars // 2
        start_idx = 0
        end_idx = len(lines)

        # Calculate start portion
        chars_count = 0
        for i in range(len(lines)):
            chars_count += len(lines[i]) + 1
            if chars_count > target_chars:
                start_idx = i
                break

        # Calculate end portion
        chars_count = 0
        for i in range(len(lines) - 1, -1, -1):
            chars_count += len(lines[i]) + 1
            if chars_count > target_chars:
                end_idx = i + 1
                break

        if start_idx < end_idx:
            removed_lines = end_idx - start_idx
            return (
                "\n".join(lines[:start_idx])
                + f"\n[TRUNCATED: {removed_lines} lines removed from middle]\n"
                + "\n".join(lines[end_idx:])
            )

    return text


def truncate_execution_result(
    result: ExecutionResult,
    max_tokens: int,
) -> ExecutionResult:
    """Truncate execution result to fit within token limit.

    Prioritizes stderr over stdout since errors are more important.

    Args:
        result: Execution result to truncate
        max_tokens: Maximum tokens for stdout + stderr combined

    Returns:
        Truncated execution result
    """
    stderr_tokens = estimate_tokens(result.stderr)
    stdout_tokens = estimate_tokens(result.stdout)
    total_tokens = stderr_tokens + stdout_tokens

    if total_tokens <= max_tokens:
        return result

    # Prioritize stderr - give it at least 70% of available tokens
    stderr_allocation = int(max_tokens * 0.7)
    stdout_allocation = max_tokens - stderr_allocation

    # If stderr is smaller, give remaining tokens to stdout
    if stderr_tokens < stderr_allocation:
        stdout_allocation = max_tokens - stderr_tokens
        truncated_stderr = result.stderr
    else:
        truncated_stderr = truncate_text(result.stderr, stderr_allocation, "end")

    # If stdout is smaller, we're done
    if stdout_tokens <= stdout_allocation:
        truncated_stdout = result.stdout
    else:
        truncated_stdout = truncate_text(result.stdout, stdout_allocation, "end")

    return replace(
        result,
        stdout=truncated_stdout,
        stderr=truncated_stderr,
    )


def truncate_commit(commit: CommitInfo, max_tokens: int) -> CommitInfo:
    """Truncate commit information to fit within token limit.

    Args:
        commit: Commit to truncate
        max_tokens: Maximum tokens allowed

    Returns:
        Truncated commit
    """
    # Keep message intact if possible, truncate diff
    message_tokens = estimate_tokens(commit.message)

    if commit.diff:
        diff_tokens = estimate_tokens(commit.diff)
        total_tokens = message_tokens + diff_tokens

        if total_tokens > max_tokens:
            # Allocate most tokens to diff since it's more informative
            diff_allocation = max(max_tokens - message_tokens, max_tokens // 2)
            truncated_diff = truncate_text(commit.diff, diff_allocation, "end")
            return replace(commit, diff=truncated_diff)

    return commit


def truncate_git_context(
    git_context: Optional[GitContext],
    max_tokens: int,
) -> Optional[GitContext]:
    """Truncate git context to fit within token limit.

    Prioritizes recent commits over older ones, and uncommitted changes
    over committed changes.

    Args:
        git_context: Git context to truncate (can be None)
        max_tokens: Maximum tokens allowed

    Returns:
        Truncated git context or None if input was None
    """
    if git_context is None:
        return None

    # Calculate current token usage
    uncommitted_tokens = estimate_tokens(git_context.uncommitted_changes)
    commits_tokens = sum(
        estimate_tokens(c.message) + estimate_tokens(c.diff or "")
        for c in git_context.recent_commits
    )
    total_tokens = uncommitted_tokens + commits_tokens

    if total_tokens <= max_tokens:
        return git_context

    # Prioritize uncommitted changes - give them 40% of tokens
    uncommitted_allocation = int(max_tokens * 0.4)
    commits_allocation = max_tokens - uncommitted_allocation

    # Truncate uncommitted changes if needed
    if uncommitted_tokens > uncommitted_allocation:
        truncated_uncommitted = truncate_text(
            git_context.uncommitted_changes,
            uncommitted_allocation,
            "end",
        )
    else:
        truncated_uncommitted = git_context.uncommitted_changes
        # Give remaining tokens to commits
        commits_allocation = max_tokens - uncommitted_tokens

    # Truncate commits - keep most recent ones, truncate older diffs first
    truncated_commits: list[CommitInfo] = []
    remaining_tokens = commits_allocation

    for commit in git_context.recent_commits:
        commit_tokens = estimate_tokens(commit.message) + estimate_tokens(
            commit.diff or ""
        )

        if commit_tokens <= remaining_tokens:
            truncated_commits.append(commit)
            remaining_tokens -= commit_tokens
        elif remaining_tokens > 0:
            # Truncate this commit to fit
            truncated_commits.append(truncate_commit(commit, remaining_tokens))
            remaining_tokens = 0
            break
        else:
            break

    return replace(
        git_context,
        recent_commits=truncated_commits,
        uncommitted_changes=truncated_uncommitted,
    )


def truncate_for_context(
    context: HealingContext,
    max_tokens: int = 100000,
) -> HealingContext:
    """Truncate healing context to fit within token limit.

    Uses intelligent prioritization to preserve the most important information:
    1. Error output (stderr) - highest priority
    2. Script content - high priority
    3. Standard output (stdout) - medium priority
    4. Uncommitted changes - medium priority
    5. Recent commits - lower priority
    6. Older commits - lowest priority

    Args:
        context: Healing context to truncate
        max_tokens: Maximum tokens allowed (default: 100,000)

    Returns:
        Truncated healing context that fits within token limit
    """
    # Calculate current token usage
    script_tokens = estimate_tokens(context.script_content)
    result_tokens = estimate_tokens(
        context.execution_result.stdout + context.execution_result.stderr
    )
    git_tokens = 0
    if context.git_context:
        git_tokens = estimate_tokens(context.git_context.uncommitted_changes)
        git_tokens += sum(
            estimate_tokens(c.message) + estimate_tokens(c.diff or "")
            for c in context.git_context.recent_commits
        )

    total_tokens = script_tokens + result_tokens + git_tokens

    # If we're within limit, return as-is
    if total_tokens <= max_tokens:
        return context

    # Allocate tokens based on priority
    # Error output: 30%, Script: 30%, Git: 25%, Stdout: 15%
    error_allocation = int(max_tokens * 0.30)
    script_allocation = int(max_tokens * 0.30)
    git_allocation = int(max_tokens * 0.25)
    stdout_allocation = max_tokens - error_allocation - script_allocation - git_allocation

    # Truncate execution result (prioritizes stderr)
    truncated_result = truncate_execution_result(
        context.execution_result,
        error_allocation + stdout_allocation,
    )

    # Truncate script content if needed
    if script_tokens > script_allocation:
        truncated_script = truncate_text(
            context.script_content,
            script_allocation,
            "middle",
        )
    else:
        truncated_script = context.script_content
        # Give remaining tokens to git context
        git_allocation += script_allocation - script_tokens

    # Truncate git context
    truncated_git = truncate_git_context(context.git_context, git_allocation)

    return replace(
        context,
        script_content=truncated_script,
        execution_result=truncated_result,
        git_context=truncated_git,
    )
