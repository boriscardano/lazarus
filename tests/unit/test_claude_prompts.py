"""Unit tests for Claude Code prompt builder."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lazarus.claude.prompts import build_healing_prompt, build_retry_prompt
from lazarus.config.schema import LazarusConfig, ScriptConfig
from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
    SystemContext,
)


def test_build_healing_prompt_basic():
    """Test building a basic healing prompt."""
    context = HealingContext(
        script_path=Path("/path/to/script.py"),
        script_content="#!/usr/bin/env python3\nprint('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/path/to"),
        ),
        config=LazarusConfig(),
    )

    prompt = build_healing_prompt(context)

    # Check that prompt includes key sections
    assert "# TASK" in prompt
    assert "# ERROR INFORMATION" in prompt
    assert "# SCRIPT" in prompt
    assert "# SYSTEM INFORMATION" in prompt
    assert "# INSTRUCTIONS" in prompt

    # Check that error details are included
    assert "SyntaxError" in prompt
    assert "exit code: 1" in prompt.lower()

    # Check that script content is included
    assert "print('hello')" in prompt


def test_build_healing_prompt_with_git_context():
    """Test building prompt with git context."""
    context = HealingContext(
        script_path=Path("/path/to/script.py"),
        script_content="print('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=GitContext(
            branch="main",
            recent_commits=[
                CommitInfo(
                    hash="abc123",
                    author="John Doe",
                    date="2024-01-30",
                    message="Fix bug",
                    diff=None,
                )
            ],
            uncommitted_changes="diff --git a/script.py\n",
            repo_root=Path("/path/to"),
        ),
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/path/to"),
        ),
        config=LazarusConfig(),
    )

    prompt = build_healing_prompt(context)

    # Check that git context is included
    assert "# GIT CONTEXT" in prompt
    assert "main" in prompt
    assert "abc123" in prompt
    assert "John Doe" in prompt


def test_build_healing_prompt_with_custom_config():
    """Test building prompt with custom script config."""
    script_config = ScriptConfig(
        name="test-script",
        path=Path("script.py"),
        description="Test script that does testing",
        custom_prompt="This script requires special handling",
        allowed_files=["script.py", "utils.py"],
        forbidden_files=["config.yaml"],
    )

    context = HealingContext(
        script_path=Path("/path/to/script.py"),
        script_content="print('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/path/to"),
        ),
        config=LazarusConfig(scripts=[script_config]),
    )

    prompt = build_healing_prompt(context)

    # Check that custom config is included
    assert "Test script that does testing" in prompt
    assert "special handling" in prompt
    assert "Allowed Files" in prompt
    assert "Forbidden Files" in prompt
    assert "config.yaml" in prompt


def test_build_healing_prompt_truncates_long_output():
    """Test that very long output is truncated."""
    long_stderr = "Error line\n" * 1000  # Very long error output

    context = HealingContext(
        script_path=Path("/path/to/script.py"),
        script_content="print('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr=long_stderr,
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/path/to"),
        ),
        config=LazarusConfig(),
    )

    prompt = build_healing_prompt(context)

    # Prompt should be shorter than the original stderr
    assert len(prompt) < len(long_stderr)
    # Should contain truncation indicator
    assert "truncated" in prompt.lower()


def test_build_retry_prompt():
    """Test building a retry prompt."""
    context = HealingContext(
        script_path=Path("/path/to/script.py"),
        script_content="print('hello')\n",
        execution_result=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.1,
            timestamp=datetime.now(UTC),
        ),
        git_context=None,
        system_context=SystemContext(
            os_name="Darwin",
            os_version="23.0.0",
            python_version="3.11.0",
            shell="/bin/bash",
            cwd=Path("/path/to"),
        ),
        config=LazarusConfig(),
    )

    previous_output = "I tried to fix it but it didn't work."
    retry_prompt = build_retry_prompt(context, previous_output, attempt_number=2)

    # Check that retry information is included
    assert "RETRY" in retry_prompt
    assert "Previous" in retry_prompt or "previous" in retry_prompt
    assert "different approach" in retry_prompt.lower()

    # Should still include base prompt elements
    assert "# TASK" in retry_prompt
    assert "# INSTRUCTIONS" in retry_prompt
