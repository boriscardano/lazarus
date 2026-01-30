"""Verification and comparison logic for script execution results.

This module provides utilities to verify script fixes by comparing execution
results, analyzing error similarities, and checking custom success criteria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal, Optional

from lazarus.core.context import ExecutionResult


@dataclass
class ErrorComparison:
    """Comparison result between two execution results.

    Attributes:
        is_same_error: Whether the errors are essentially the same
        similarity_score: Similarity score between 0 (completely different) and 1 (identical)
        key_differences: List of identified key differences between the errors
    """

    is_same_error: bool
    similarity_score: float
    key_differences: list[str]


@dataclass
class VerificationResult:
    """Result of verifying a script fix.

    Attributes:
        status: Verification status indicating the outcome
        execution_result: The execution result from the verification run
        comparison: Comparison between previous and current execution
        custom_criteria_passed: Whether custom success criteria passed (None if no criteria)
    """

    status: Literal["success", "same_error", "different_error", "timeout"]
    execution_result: ExecutionResult
    comparison: ErrorComparison
    custom_criteria_passed: Optional[bool]


def compare_errors(previous: ExecutionResult, current: ExecutionResult) -> ErrorComparison:
    """Compare two execution results to determine error similarity.

    This function analyzes exit codes, stderr patterns, and output similarities
    to determine if two script executions produced the same error or different ones.

    Args:
        previous: The previous execution result (before fix attempt)
        current: The current execution result (after fix attempt)

    Returns:
        ErrorComparison with similarity analysis and key differences

    Example:
        >>> prev = ExecutionResult(exit_code=1, stdout="", stderr="File not found: data.txt", duration=0.1)
        >>> curr = ExecutionResult(exit_code=1, stdout="", stderr="File not found: data.txt", duration=0.1)
        >>> comparison = compare_errors(prev, curr)
        >>> comparison.is_same_error
        True
        >>> comparison.similarity_score > 0.9
        True
    """
    key_differences: list[str] = []

    # Compare exit codes
    exit_code_same = previous.exit_code == current.exit_code
    if not exit_code_same:
        key_differences.append(
            f"Exit code changed from {previous.exit_code} to {current.exit_code}"
        )

    # Normalize stderr for comparison (remove timestamps, paths, etc.)
    prev_stderr_normalized = _normalize_error_output(previous.stderr)
    curr_stderr_normalized = _normalize_error_output(current.stderr)

    # Calculate similarity using SequenceMatcher
    stderr_similarity = SequenceMatcher(
        None, prev_stderr_normalized, curr_stderr_normalized
    ).ratio()

    # Also check stdout similarity for cases where errors are logged to stdout
    prev_stdout_normalized = _normalize_error_output(previous.stdout)
    curr_stdout_normalized = _normalize_error_output(current.stdout)
    stdout_similarity = SequenceMatcher(
        None, prev_stdout_normalized, curr_stdout_normalized
    ).ratio()

    # Overall similarity is weighted towards stderr (more important for errors)
    overall_similarity = (stderr_similarity * 0.7) + (stdout_similarity * 0.3)

    # Extract error patterns from stderr
    prev_error_patterns = _extract_error_patterns(previous.stderr)
    curr_error_patterns = _extract_error_patterns(current.stderr)

    # Check for missing or new error patterns
    missing_patterns = prev_error_patterns - curr_error_patterns
    new_patterns = curr_error_patterns - prev_error_patterns

    if missing_patterns:
        key_differences.append(
            f"Error patterns no longer present: {', '.join(sorted(missing_patterns))}"
        )

    if new_patterns:
        key_differences.append(
            f"New error patterns appeared: {', '.join(sorted(new_patterns))}"
        )

    # Determine if it's the same error
    # Consider it the same error if:
    # 1. Exit codes match AND stderr similarity is high (>0.8), OR
    # 2. Error patterns are identical AND similarity is reasonably high (>0.6)
    is_same_error = (
        exit_code_same and stderr_similarity > 0.8
    ) or (
        not missing_patterns
        and not new_patterns
        and prev_error_patterns
        and overall_similarity > 0.6
    )

    return ErrorComparison(
        is_same_error=is_same_error,
        similarity_score=overall_similarity,
        key_differences=key_differences,
    )


def check_custom_criteria(result: ExecutionResult, criteria: dict[str, Any]) -> bool:
    """Check if execution result meets custom success criteria.

    Supports various criteria types:
    - exit_code: Expected exit code (e.g., {"exit_code": 0})
    - contains: Pattern that should appear in stdout (e.g., {"contains": "Success"})
    - not_contains: Pattern that should NOT appear in stderr (e.g., {"not_contains": "Error"})
    - regex_match: Regex pattern to match in stdout (e.g., {"regex_match": "Processed \\d+ items"})

    Args:
        result: The execution result to check
        criteria: Dictionary of success criteria

    Returns:
        True if all criteria are met, False otherwise

    Example:
        >>> result = ExecutionResult(exit_code=0, stdout="Success: 100 items", stderr="", duration=1.0)
        >>> check_custom_criteria(result, {"exit_code": 0, "contains": "Success"})
        True
        >>> check_custom_criteria(result, {"not_contains": "Error"})
        True
        >>> check_custom_criteria(result, {"regex_match": r"\\d+ items"})
        True
    """
    # Check exit_code criterion
    if "exit_code" in criteria:
        expected_code = criteria["exit_code"]
        if result.exit_code != expected_code:
            return False

    # Check contains criterion (check stdout)
    if "contains" in criteria:
        pattern = str(criteria["contains"])
        if pattern not in result.stdout:
            return False

    # Check not_contains criterion (check both stdout and stderr)
    if "not_contains" in criteria:
        pattern = str(criteria["not_contains"])
        if pattern in result.stdout or pattern in result.stderr:
            return False

    # Check regex_match criterion (check stdout)
    if "regex_match" in criteria:
        pattern = str(criteria["regex_match"])
        try:
            if not re.search(pattern, result.stdout):
                return False
        except re.error:
            # Invalid regex pattern - treat as not matching
            return False

    # Check stderr_contains criterion (check stderr specifically)
    if "stderr_contains" in criteria:
        pattern = str(criteria["stderr_contains"])
        if pattern not in result.stderr:
            return False

    # Check stderr_not_contains criterion
    if "stderr_not_contains" in criteria:
        pattern = str(criteria["stderr_not_contains"])
        if pattern in result.stderr:
            return False

    # Check duration_less_than criterion
    if "duration_less_than" in criteria:
        max_duration = float(criteria["duration_less_than"])
        if result.duration >= max_duration:
            return False

    # All criteria passed
    return True


def _normalize_error_output(output: str) -> str:
    """Normalize error output for comparison.

    Removes or normalizes elements that may vary between runs:
    - Timestamps
    - Absolute file paths (replace with relative markers)
    - Process IDs
    - Memory addresses
    - Line numbers in some error formats

    Args:
        output: Raw error output

    Returns:
        Normalized output for comparison
    """
    if not output:
        return ""

    normalized = output

    # Remove common timestamp patterns
    # ISO format: 2024-01-30T12:34:56.789Z
    normalized = re.sub(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",
        "[TIMESTAMP]",
        normalized,
    )
    # Unix timestamp: 1706623696
    normalized = re.sub(r"\b\d{10,13}\b", "[TIMESTAMP]", normalized)

    # Normalize file paths - replace absolute paths with relative markers
    # Unix paths
    normalized = re.sub(r"/(?:home|Users|usr|opt)/[^\s:,]+", "[PATH]", normalized)
    # Windows paths
    normalized = re.sub(r"[A-Z]:\\[^\s:,]+", "[PATH]", normalized)

    # Remove process IDs
    normalized = re.sub(r"\bpid[:\s=]+\d+", "pid=[PID]", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bprocess\s+\d+", "process [PID]", normalized, flags=re.IGNORECASE)

    # Remove memory addresses
    normalized = re.sub(r"0x[0-9a-fA-F]+", "[ADDR]", normalized)

    # Remove port numbers in URLs/connections
    normalized = re.sub(r":(\d{2,5})\b", ":[PORT]", normalized)

    # Normalize common variations in error messages
    normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace
    normalized = normalized.strip()

    return normalized


def _extract_error_patterns(output: str) -> set[str]:
    """Extract common error patterns from output.

    Identifies error indicators like:
    - Error types (e.g., "FileNotFoundError", "TypeError")
    - Error keywords (e.g., "ERROR:", "Failed:", "Exception:")
    - HTTP status codes in error context

    Args:
        output: Error output to analyze

    Returns:
        Set of error pattern identifiers found in the output
    """
    if not output:
        return set()

    patterns = set()

    # Python exception types
    python_exceptions = re.findall(
        r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)*Error|[A-Z][a-z]+Exception)\b", output
    )
    patterns.update(python_exceptions)

    # JavaScript error types
    js_errors = re.findall(
        r"\b(Error|TypeError|ReferenceError|SyntaxError|RangeError)\b", output
    )
    patterns.update(js_errors)

    # Common error keywords
    error_keywords = re.findall(
        r"\b(ERROR|FATAL|CRITICAL|FAILED|FAILURE|Exception|error|failed)\b", output
    )
    patterns.update(error_keywords)

    # HTTP error status codes (4xx, 5xx)
    http_errors = re.findall(r"\b([45]\d{2})\b", output)
    patterns.update(f"HTTP_{code}" for code in http_errors)

    # Common error phrases
    if "not found" in output.lower():
        patterns.add("not_found")
    if "permission denied" in output.lower():
        patterns.add("permission_denied")
    if "connection refused" in output.lower():
        patterns.add("connection_refused")
    if "timeout" in output.lower():
        patterns.add("timeout")
    if "no such file" in output.lower():
        patterns.add("file_missing")
    if "cannot connect" in output.lower():
        patterns.add("connection_failed")

    return patterns
