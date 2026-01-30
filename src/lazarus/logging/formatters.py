"""Log formatters and display utilities for Lazarus.

This module provides formatting utilities for displaying healing results
in the CLI with rich formatting and JSON output.
"""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from lazarus.core.healer import HealingResult


def format_healing_summary(result: HealingResult) -> str:
    """Format a healing result as a human-readable summary.

    Args:
        result: HealingResult to format

    Returns:
        Formatted summary string suitable for CLI display

    Example:
        >>> summary = format_healing_summary(result)
        >>> print(summary)
        Healing Result: Success
        Attempts: 2
        Duration: 45.3s
        PR URL: https://github.com/user/repo/pull/123
    """
    lines = []

    # Status
    status = "Success" if result.success else "Failed"
    lines.append(f"Healing Result: {status}")

    # Basic stats
    lines.append(f"Attempts: {len(result.attempts)}")
    lines.append(f"Duration: {result.duration:.1f}s")

    # PR URL if available
    if result.pr_url:
        lines.append(f"PR URL: {result.pr_url}")

    # Error message if failed
    if not result.success and result.error_message:
        lines.append(f"Error: {result.error_message}")

    # Attempt details
    if result.attempts:
        lines.append("")
        lines.append("Attempts:")
        for attempt in result.attempts:
            lines.append(
                f"  {attempt.attempt_number}. {attempt.verification.status} "
                f"({attempt.duration:.1f}s)"
            )
            if attempt.claude_response.explanation:
                # Truncate long explanations
                explanation = attempt.claude_response.explanation
                if len(explanation) > 80:
                    explanation = explanation[:77] + "..."
                lines.append(f"     {explanation}")

    return "\n".join(lines)


def format_healing_json(result: HealingResult) -> str:
    """Format a healing result as JSON.

    Args:
        result: HealingResult to format

    Returns:
        JSON string representation of the result

    Example:
        >>> json_output = format_healing_json(result)
        >>> data = json.loads(json_output)
    """
    data = {
        "success": result.success,
        "duration": result.duration,
        "attempts": [
            {
                "attempt_number": attempt.attempt_number,
                "status": attempt.verification.status,
                "duration": attempt.duration,
                "files_changed": attempt.claude_response.files_changed,
                "explanation": attempt.claude_response.explanation,
            }
            for attempt in result.attempts
        ],
        "pr_url": result.pr_url,
        "error_message": result.error_message,
    }
    return json.dumps(data, indent=2)


def display_healing_result_table(
    result: HealingResult,
    console: Console | None = None,
) -> None:
    """Display healing result as a rich table.

    Args:
        result: HealingResult to display
        console: Optional Rich console (creates one if not provided)

    Example:
        >>> display_healing_result_table(result)
    """
    if console is None:
        console = Console()

    # Create table
    table = Table(title="Healing Result", show_header=True)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green" if result.success else "red")

    # Add rows
    status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
    table.add_row("Status", status)
    table.add_row("Attempts", str(len(result.attempts)))
    table.add_row("Duration", f"{result.duration:.2f}s")

    if result.pr_url:
        table.add_row("PR URL", result.pr_url)

    if result.error_message:
        table.add_row("Error", result.error_message)

    console.print(table)

    # Show attempts if any
    if result.attempts:
        console.print("\n[bold]Attempts:[/bold]")
        attempts_table = Table(show_header=True)
        attempts_table.add_column("#", style="cyan", justify="right")
        attempts_table.add_column("Status", style="yellow")
        attempts_table.add_column("Duration", justify="right")
        attempts_table.add_column("Description")

        for attempt in result.attempts:
            status_style = (
                "[green]" if attempt.verification.status == "success" else "[yellow]"
            )
            attempts_table.add_row(
                str(attempt.attempt_number),
                f"{status_style}{attempt.verification.status}[/]",
                f"{attempt.duration:.1f}s",
                attempt.claude_response.explanation or "",
            )

        console.print(attempts_table)
