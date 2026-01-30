"""Prompt templates for Claude Code healing requests.

This module provides functions to build structured prompts for Claude Code,
incorporating all relevant context from the failed script execution.
"""

from __future__ import annotations

from lazarus.core.context import HealingContext


def build_healing_prompt(context: HealingContext) -> str:
    """Build a structured healing prompt for Claude Code.

    This function creates a comprehensive prompt that includes:
    - Clear task definition
    - Error information (stdout, stderr, exit code)
    - Script content
    - Git context (recent changes, uncommitted modifications)
    - System information
    - Constraints and instructions

    Args:
        context: Complete healing context with all relevant information

    Returns:
        Formatted prompt string ready to send to Claude Code
    """
    prompt_parts = []

    # Task section
    prompt_parts.append("# TASK")
    prompt_parts.append(
        f"Fix the failing script at: {context.script_path}\n"
    )
    if context.config.scripts:
        # Try to find matching script config
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].description:
            prompt_parts.append(f"Description: {script_configs[0].description}\n")

    # Error section
    prompt_parts.append("# ERROR INFORMATION")
    prompt_parts.append(f"Exit Code: {context.execution_result.exit_code}")
    prompt_parts.append(f"Duration: {context.execution_result.duration:.2f}s")
    prompt_parts.append(f"Timestamp: {context.execution_result.timestamp.isoformat()}\n")

    if context.execution_result.stdout.strip():
        prompt_parts.append("## Standard Output:")
        prompt_parts.append("```")
        # Truncate very long output
        stdout = context.execution_result.stdout
        if len(stdout) > 5000:
            stdout = stdout[:2500] + "\n\n... [truncated] ...\n\n" + stdout[-2500:]
        prompt_parts.append(stdout)
        prompt_parts.append("```\n")

    if context.execution_result.stderr.strip():
        prompt_parts.append("## Standard Error:")
        prompt_parts.append("```")
        # Truncate very long error output
        stderr = context.execution_result.stderr
        if len(stderr) > 5000:
            stderr = stderr[:2500] + "\n\n... [truncated] ...\n\n" + stderr[-2500:]
        prompt_parts.append(stderr)
        prompt_parts.append("```\n")

    # Script section
    prompt_parts.append("# SCRIPT")
    prompt_parts.append(f"File: {context.script_path}")
    prompt_parts.append("```")
    prompt_parts.append(context.script_content)
    prompt_parts.append("```\n")

    # Git context section
    if context.git_context:
        prompt_parts.append("# GIT CONTEXT")
        prompt_parts.append(f"Branch: {context.git_context.branch}")
        prompt_parts.append(f"Repository: {context.git_context.repo_root}\n")

        if context.git_context.recent_commits:
            prompt_parts.append("## Recent Commits:")
            for i, commit in enumerate(context.git_context.recent_commits[:3], 1):
                prompt_parts.append(f"{i}. {commit.hash[:8]} - {commit.message}")
                prompt_parts.append(f"   by {commit.author} on {commit.date}")
                if commit.diff and len(commit.diff) < 2000:
                    # Only include compact diffs
                    prompt_parts.append(f"   Changes:\n{commit.diff[:1000]}")
            prompt_parts.append("")

        if context.git_context.uncommitted_changes.strip():
            prompt_parts.append("## Uncommitted Changes:")
            prompt_parts.append("```diff")
            # Truncate large diffs
            changes = context.git_context.uncommitted_changes
            if len(changes) > 3000:
                changes = changes[:1500] + "\n\n... [truncated] ...\n\n" + changes[-1500:]
            prompt_parts.append(changes)
            prompt_parts.append("```\n")

    # System section
    prompt_parts.append("# SYSTEM INFORMATION")
    prompt_parts.append(f"OS: {context.system_context.os_name}")
    prompt_parts.append(f"OS Version: {context.system_context.os_version}")
    prompt_parts.append(f"Python: {context.system_context.python_version.split()[0]}")
    prompt_parts.append(f"Shell: {context.system_context.shell}")
    prompt_parts.append(f"Working Directory: {context.system_context.cwd}\n")

    # Success criteria (if defined)
    if context.config.scripts:
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].success_criteria:
            prompt_parts.append("# SUCCESS CRITERIA")
            criteria = script_configs[0].success_criteria
            for key, value in criteria.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

    # Custom prompt section (if provided)
    if context.config.scripts:
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].custom_prompt:
            prompt_parts.append("# ADDITIONAL CONTEXT")
            prompt_parts.append(script_configs[0].custom_prompt)
            prompt_parts.append("")

    # Previous attempts section
    if context.previous_attempts:
        prompt_parts.append("# PREVIOUS HEALING ATTEMPTS")
        prompt_parts.append(
            "This script has been attempted before. Here's what was tried:\n"
        )

        for attempt in context.previous_attempts:
            prompt_parts.append(f"## Attempt {attempt.attempt_number}:")
            prompt_parts.append(f"What was tried: {attempt.claude_response_summary}")

            if attempt.changes_made:
                prompt_parts.append("Files modified:")
                for file in attempt.changes_made:
                    prompt_parts.append(f"  - {file}")

            prompt_parts.append("Result: Still failed with error:")
            prompt_parts.append("```")
            # Truncate very long errors
            error = attempt.error_after
            if len(error) > 1000:
                error = error[:500] + "\n... [truncated] ...\n" + error[-500:]
            prompt_parts.append(error)
            prompt_parts.append("```\n")

        prompt_parts.append(
            "IMPORTANT: The above approaches did NOT work. "
            "Please try a DIFFERENT approach or technique.\n"
        )

    # Instructions section
    prompt_parts.append("# INSTRUCTIONS")
    prompt_parts.append(
        "1. Analyze the error and identify the root cause\n"
        "2. Make ONLY the minimal changes necessary to fix the issue\n"
        "3. DO NOT refactor or improve unrelated code\n"
        "4. DO NOT add features or make style changes\n"
        "5. Preserve the original intent and logic of the script\n"
        "6. After making changes, briefly explain what you fixed and why\n"
    )

    # File constraints (if defined)
    if context.config.scripts:
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs:
            config = script_configs[0]
            if config.allowed_files:
                prompt_parts.append("\n## Allowed Files:")
                prompt_parts.append("You may only modify these files:")
                for pattern in config.allowed_files:
                    prompt_parts.append(f"- {pattern}")

            if config.forbidden_files:
                prompt_parts.append("\n## Forbidden Files:")
                prompt_parts.append("You must NEVER modify these files:")
                for pattern in config.forbidden_files:
                    prompt_parts.append(f"- {pattern}")

    # Add emphasis on minimal changes
    prompt_parts.append(
        "\nRemember: Be surgical and precise. Fix only what's broken."
    )

    return "\n".join(prompt_parts)


def build_diagnosis_prompt(context: HealingContext) -> str:
    """Build a diagnosis-only prompt for Claude Code.

    This creates a prompt specifically for diagnosing issues without making
    any changes to files. It asks Claude to analyze and explain what's wrong.

    Args:
        context: Complete healing context with all relevant information

    Returns:
        Formatted diagnosis prompt string
    """
    prompt_parts = []

    # Task section
    prompt_parts.append("# TASK")
    prompt_parts.append(
        f"Diagnose what's wrong with the failing script at: {context.script_path}\n"
    )
    prompt_parts.append(
        "IMPORTANT: This is a DIAGNOSIS ONLY task. DO NOT modify any files.\n"
        "Instead, provide a detailed analysis of what's wrong and what would need to be fixed.\n"
    )

    if context.config.scripts:
        # Try to find matching script config
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].description:
            prompt_parts.append(f"Description: {script_configs[0].description}\n")

    # Error section
    prompt_parts.append("# ERROR INFORMATION")
    prompt_parts.append(f"Exit Code: {context.execution_result.exit_code}")
    prompt_parts.append(f"Duration: {context.execution_result.duration:.2f}s")
    prompt_parts.append(f"Timestamp: {context.execution_result.timestamp.isoformat()}\n")

    if context.execution_result.stdout.strip():
        prompt_parts.append("## Standard Output:")
        prompt_parts.append("```")
        # Truncate very long output
        stdout = context.execution_result.stdout
        if len(stdout) > 5000:
            stdout = stdout[:2500] + "\n\n... [truncated] ...\n\n" + stdout[-2500:]
        prompt_parts.append(stdout)
        prompt_parts.append("```\n")

    if context.execution_result.stderr.strip():
        prompt_parts.append("## Standard Error:")
        prompt_parts.append("```")
        # Truncate very long error output
        stderr = context.execution_result.stderr
        if len(stderr) > 5000:
            stderr = stderr[:2500] + "\n\n... [truncated] ...\n\n" + stderr[-2500:]
        prompt_parts.append(stderr)
        prompt_parts.append("```\n")

    # Script section
    prompt_parts.append("# SCRIPT")
    prompt_parts.append(f"File: {context.script_path}")
    prompt_parts.append("```")
    prompt_parts.append(context.script_content)
    prompt_parts.append("```\n")

    # Git context section
    if context.git_context:
        prompt_parts.append("# GIT CONTEXT")
        prompt_parts.append(f"Branch: {context.git_context.branch}")
        prompt_parts.append(f"Repository: {context.git_context.repo_root}\n")

        if context.git_context.recent_commits:
            prompt_parts.append("## Recent Commits:")
            for i, commit in enumerate(context.git_context.recent_commits[:3], 1):
                prompt_parts.append(f"{i}. {commit.hash[:8]} - {commit.message}")
                prompt_parts.append(f"   by {commit.author} on {commit.date}")
                if commit.diff and len(commit.diff) < 2000:
                    # Only include compact diffs
                    prompt_parts.append(f"   Changes:\n{commit.diff[:1000]}")
            prompt_parts.append("")

        if context.git_context.uncommitted_changes.strip():
            prompt_parts.append("## Uncommitted Changes:")
            prompt_parts.append("```diff")
            # Truncate large diffs
            changes = context.git_context.uncommitted_changes
            if len(changes) > 3000:
                changes = changes[:1500] + "\n\n... [truncated] ...\n\n" + changes[-1500:]
            prompt_parts.append(changes)
            prompt_parts.append("```\n")

    # System section
    prompt_parts.append("# SYSTEM INFORMATION")
    prompt_parts.append(f"OS: {context.system_context.os_name}")
    prompt_parts.append(f"OS Version: {context.system_context.os_version}")
    prompt_parts.append(f"Python: {context.system_context.python_version.split()[0]}")
    prompt_parts.append(f"Shell: {context.system_context.shell}")
    prompt_parts.append(f"Working Directory: {context.system_context.cwd}\n")

    # Success criteria (if defined)
    if context.config.scripts:
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].success_criteria:
            prompt_parts.append("# SUCCESS CRITERIA")
            criteria = script_configs[0].success_criteria
            for key, value in criteria.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

    # Custom prompt section (if provided)
    if context.config.scripts:
        script_configs = [
            s for s in context.config.scripts
            if s.path.name == context.script_path.name
        ]
        if script_configs and script_configs[0].custom_prompt:
            prompt_parts.append("# ADDITIONAL CONTEXT")
            prompt_parts.append(script_configs[0].custom_prompt)
            prompt_parts.append("")

    # Instructions section for diagnosis
    prompt_parts.append("# INSTRUCTIONS")
    prompt_parts.append(
        "Please provide a detailed diagnosis including:\n"
        "1. What is the root cause of the error?\n"
        "2. Why is this error happening?\n"
        "3. What would need to be changed to fix it?\n"
        "4. Are there any related issues or concerns?\n"
        "5. What is the recommended approach to fix this?\n\n"
        "Remember: This is DIAGNOSIS ONLY - do not modify any files.\n"
        "Explain what's wrong in clear, actionable terms."
    )

    return "\n".join(prompt_parts)


def build_retry_prompt(
    context: HealingContext,
    previous_attempt_output: str,
    attempt_number: int,
) -> str:
    """Build a prompt for retrying a failed healing attempt.

    This creates a modified prompt that includes information about previous
    attempts, helping Claude understand what was already tried.

    Args:
        context: Complete healing context
        previous_attempt_output: Output from the previous attempt
        attempt_number: Current attempt number (starting from 2)

    Returns:
        Formatted retry prompt string
    """
    base_prompt = build_healing_prompt(context)

    # Add retry context
    retry_section = [
        f"\n# RETRY ATTEMPT {attempt_number}",
        "Previous healing attempt did not succeed.",
        "",
        "## Previous Attempt Output:",
        "```",
        previous_attempt_output[:2000],  # Truncate if too long
        "```",
        "",
        "Please try a different approach to fix this issue.",
        "Review what might have been missed in the previous attempt.",
    ]

    # Insert retry section before instructions
    if "# INSTRUCTIONS" in base_prompt:
        parts = base_prompt.split("# INSTRUCTIONS")
        return parts[0] + "\n".join(retry_section) + "\n\n# INSTRUCTIONS" + parts[1]
    else:
        return base_prompt + "\n" + "\n".join(retry_section)
