"""Output parsing and change detection for Claude Code responses.

This module provides functionality to parse Claude Code output, detect file
changes, and extract explanations from the AI's responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClaudeResponse:
    """Response from Claude Code after attempting to fix a script.

    Attributes:
        success: Whether Claude successfully fixed the issue
        explanation: Claude's explanation of what was fixed
        files_changed: List of file paths that were modified
        error_message: Error message if the healing attempt failed
        raw_output: Complete raw output from Claude Code (stdout + stderr)
    """

    success: bool
    explanation: str
    files_changed: list[str]
    error_message: str | None
    raw_output: str


def parse_claude_output(stdout: str, stderr: str, exit_code: int) -> ClaudeResponse:
    """Parse Claude Code output to extract healing results.

    This function analyzes the output from Claude Code to determine:
    - Whether the healing attempt was successful
    - What files were changed during the healing process
    - Claude's explanation of what was fixed
    - Any error messages if the attempt failed

    Args:
        stdout: Standard output from the Claude Code process
        stderr: Standard error from the Claude Code process
        exit_code: Exit code from the Claude Code process

    Returns:
        ClaudeResponse with parsed information about the healing attempt
    """
    raw_output = f"{stdout}\n{stderr}".strip()

    # Check for authentication errors
    auth_error_patterns = [
        r"authentication failed",
        r"invalid api key",
        r"unauthorized",
        r"not authenticated",
        r"login required",
        r"session expired",
    ]
    for pattern in auth_error_patterns:
        if re.search(pattern, raw_output, re.IGNORECASE):
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message="Claude Code authentication failed. Please run 'claude login' first.",
                raw_output=raw_output,
            )

    # Check for rate limit errors
    rate_limit_patterns = [
        r"rate limit",
        r"too many requests",
        r"quota exceeded",
        r"overloaded_error",
    ]
    for pattern in rate_limit_patterns:
        if re.search(pattern, raw_output, re.IGNORECASE):
            return ClaudeResponse(
                success=False,
                explanation="",
                files_changed=[],
                error_message="Claude Code rate limit exceeded. Please try again later.",
                raw_output=raw_output,
            )

    # Check for timeout or other errors
    if exit_code != 0:
        # Try to extract a meaningful error message from stderr
        error_lines = [line.strip() for line in stderr.split("\n") if line.strip()]
        error_message = error_lines[-1] if error_lines else f"Claude Code exited with code {exit_code}"

        return ClaudeResponse(
            success=False,
            explanation="",
            files_changed=[],
            error_message=error_message,
            raw_output=raw_output,
        )

    # Parse successful output
    files_changed = _extract_changed_files(stdout)
    explanation = _extract_explanation(stdout)

    # Determine success based on whether changes were made
    # If Claude ran successfully (exit_code 0) but made no changes,
    # it might mean it couldn't fix the issue or thought no fix was needed
    success = len(files_changed) > 0

    return ClaudeResponse(
        success=success,
        explanation=explanation,
        files_changed=files_changed,
        error_message=None if success else "No changes were made by Claude Code",
        raw_output=raw_output,
    )


def _extract_changed_files(output: str) -> list[str]:
    """Extract list of changed files from Claude Code output.

    Claude Code typically indicates file changes with patterns like:
    - "Edited file.py"
    - "Modified: file.py"
    - "Updated file.py"
    - "Wrote to file.py"
    - Tool calls like Edit[file_path="/path/to/file.py"]

    Args:
        output: Claude Code stdout output

    Returns:
        List of file paths that were changed
    """
    files = []

    # Pattern 1: Tool usage indicators (Edit, Write tools)
    # Example: Edit[file_path="/path/to/file.py"]
    tool_patterns = [
        r'Edit\[file_path=["\']([^"\']+)["\']',
        r'Write\[file_path=["\']([^"\']+)["\']',
    ]
    for pattern in tool_patterns:
        matches = re.findall(pattern, output)
        files.extend(matches)

    # Pattern 2: Action descriptions
    # Example: "Edited /path/to/file.py" or "Modified file.py"
    action_patterns = [
        r'(?:Edited|Modified|Updated|Wrote to)\s+([^\s,\n]+\.(?:py|sh|js|ts|yaml|yml|json|toml|md))',
        r'(?:Edited|Modified|Updated|Wrote to)\s+"([^"]+)"',
        r'(?:Edited|Modified|Updated|Wrote to)\s+`([^`]+)`',
    ]
    for pattern in action_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        files.extend(matches)

    # Pattern 3: File path mentions in context of changes
    # Look for file paths after verbs indicating modification
    change_context_pattern = r'(?:changed|fixed|updated|modified|edited)\s+(?:the\s+)?(?:file\s+)?([^\s,\n]+\.(?:py|sh|js|ts|yaml|yml|json|toml|md))'
    matches = re.findall(change_context_pattern, output, re.IGNORECASE)
    files.extend(matches)

    # Pattern 4: Success messages with file paths
    # Example: "Successfully updated /path/to/file.py"
    success_pattern = r'Successfully\s+(?:updated|modified|edited|changed)\s+([^\s,\n]+\.(?:py|sh|js|ts|yaml|yml|json|toml|md))'
    matches = re.findall(success_pattern, output, re.IGNORECASE)
    files.extend(matches)

    # Deduplicate and clean up file paths
    unique_files = list(dict.fromkeys(files))  # Preserve order while removing duplicates

    # Filter out common false positives
    filtered_files = [
        f for f in unique_files
        if not any(exclude in f.lower() for exclude in ["example", "template", "sample"])
    ]

    return filtered_files


def _extract_explanation(output: str) -> str:
    """Extract Claude's explanation of what was fixed.

    Looks for natural language explanations in the output, typically
    found in the response text before or after tool usage.

    Args:
        output: Claude Code stdout output

    Returns:
        Explanation string, or a default message if none found
    """
    # Try to find explanation sections
    # Claude often starts explanations with phrases like:
    # - "I've fixed..."
    # - "The issue was..."
    # - "I've updated..."
    # - "The problem was..."

    explanation_patterns = [
        r"((?:I've|I have)\s+(?:fixed|updated|modified|changed)\s+[^.!?\n]+[.!?])",
        r"((?:The\s+)?(?:issue|problem|error)\s+(?:was|is)\s+[^.!?\n]+[.!?])",
        r"((?:Fixed|Updated|Modified|Changed)\s+[^.!?\n]+[.!?])",
        r"((?:To fix this|The fix),?\s+I\s+[^.!?\n]+[.!?])",
    ]

    explanations = []
    for pattern in explanation_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        explanations.extend(matches)

    if explanations:
        # Combine the first few explanations into a coherent message
        return " ".join(explanations[:3])

    # Try to extract the first substantial paragraph (at least 50 chars)
    paragraphs = [p.strip() for p in output.split("\n\n") if len(p.strip()) >= 50]
    if paragraphs:
        # Find the first paragraph that looks like an explanation
        # (contains action verbs and file-related words)
        for para in paragraphs[:5]:
            if any(word in para.lower() for word in ["fix", "change", "update", "modify", "error", "issue", "problem"]):
                # Truncate to reasonable length
                if len(para) > 300:
                    para = para[:297] + "..."
                return para

        # Fall back to first paragraph if no explanation-like paragraph found
        first_para = paragraphs[0]
        if len(first_para) > 300:
            first_para = first_para[:297] + "..."
        return first_para

    # If we can't find a good explanation, return a generic message
    return "Claude Code completed the healing attempt."
