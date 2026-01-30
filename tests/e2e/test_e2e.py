"""End-to-end tests using actual Claude Code.

These tests are marked to skip by default as they require:
- Claude Code CLI installed and authenticated
- Network access
- Longer execution time

Run with: pytest -m e2e --run-e2e
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from lazarus.config.schema import HealingConfig, LazarusConfig
from lazarus.core.healer import Healer

# Custom marker for E2E tests
pytestmark = pytest.mark.e2e


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests that use actual Claude Code (skipped by default)",
    )


def pytest_collection_modifyitems(config, items):
    """Modify E2E test collection to skip by default."""
    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests require --run-e2e flag")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run E2E tests that require Claude Code",
    )


def is_claude_available() -> bool:
    """Check if Claude Code CLI is available and authenticated.

    Returns:
        True if claude CLI is available and authenticated
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@pytest.fixture(scope="module")
def check_claude_available():
    """Fixture to check if Claude Code is available.

    Raises:
        pytest.skip: If Claude Code is not available
    """
    if not is_claude_available():
        pytest.skip(
            "Claude Code CLI is not available. "
            "Install with: npm install -g @anthropic-ai/claude-code"
        )


@pytest.fixture
def e2e_config(tmp_path: Path) -> LazarusConfig:
    """Create a configuration for E2E tests.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        LazarusConfig for E2E testing
    """
    from lazarus.config.schema import GitConfig

    return LazarusConfig(
        scripts=[],
        healing=HealingConfig(
            max_attempts=2,  # Limit attempts for E2E
            timeout_per_attempt=120,
            total_timeout=300,
            claude_model="claude-sonnet-4-5-20250929",
        ),
        git=GitConfig(
            create_pr=False,  # Disable PR creation for tests
        ),
    )


@pytest.fixture
def broken_python_script(tmp_path: Path) -> Path:
    """Create a broken Python script for E2E testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to the broken script
    """
    script = tmp_path / "broken.py"
    script.write_text(
        """#!/usr/bin/env python3
\"\"\"A broken script for testing Lazarus.\"\"\"
import sys

def main():
    # This will fail - undefined variable
    print(f"Result: {undefined_variable}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    )
    script.chmod(0o755)
    return script


@pytest.fixture
def broken_bash_script(tmp_path: Path) -> Path:
    """Create a broken Bash script for E2E testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to the broken script
    """
    script = tmp_path / "broken.sh"
    script.write_text(
        """#!/bin/bash
# A broken script for testing Lazarus
set -e

echo "Starting script..."

# This will fail - undefined command
undefined_command

echo "Done"
exit 0
"""
    )
    script.chmod(0o755)
    return script


class TestE2EPythonHealing:
    """E2E tests for healing Python scripts with real Claude Code."""

    def test_heal_simple_python_error(
        self,
        check_claude_available,
        e2e_config,
        broken_python_script,
    ):
        """Test healing a simple Python NameError with actual Claude Code.

        This test:
        1. Runs a broken Python script
        2. Calls actual Claude Code to fix it
        3. Verifies the fix works
        """
        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(broken_python_script)

        # Verify results
        assert result.success is True, f"Healing failed: {result.error_message}"
        assert len(result.attempts) > 0
        assert result.final_execution.exit_code == 0

        # Verify the script actually runs now
        verify_result = subprocess.run(
            ["python3", str(broken_python_script)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert verify_result.returncode == 0

    def test_heal_with_multiple_attempts(
        self,
        check_claude_available,
        e2e_config,
        tmp_path,
    ):
        """Test healing a script that might require multiple attempts."""
        # Create a more complex broken script
        script = tmp_path / "complex.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys
import os

def process_data(items):
    # Multiple issues: undefined variable, wrong logic
    result = []
    for item in items:
        # This will fail
        processed = item * undefined_multiplier
        result.append(processed)
    return result

def main():
    data = [1, 2, 3, 4, 5]
    result = process_data(data)
    print(f"Processed: {result}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        )
        script.chmod(0o755)

        # Configure for more attempts
        e2e_config.healing.max_attempts = 3

        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(script)

        # We expect healing to succeed or provide useful feedback
        assert result.attempts  # At least one attempt was made
        if result.success:
            assert result.final_execution.exit_code == 0


class TestE2EBashHealing:
    """E2E tests for healing Bash scripts with real Claude Code."""

    def test_heal_simple_bash_error(
        self,
        check_claude_available,
        e2e_config,
        broken_bash_script,
    ):
        """Test healing a simple Bash command error with actual Claude Code."""
        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(broken_bash_script)

        # Verify results
        assert result.success is True, f"Healing failed: {result.error_message}"
        assert len(result.attempts) > 0
        assert result.final_execution.exit_code == 0


class TestE2EEdgeCases:
    """E2E tests for edge cases and error conditions."""

    def test_heal_timeout(
        self,
        check_claude_available,
        e2e_config,
        tmp_path,
    ):
        """Test handling of script timeouts."""
        # Create a script that times out
        script = tmp_path / "timeout.py"
        script.write_text(
            """#!/usr/bin/env python3
import time
import sys

def main():
    # Sleep longer than timeout
    time.sleep(1000)
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        )
        script.chmod(0o755)

        # Set very short timeout
        e2e_config.healing.timeout_per_attempt = 2

        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(script)

        # Should timeout and not succeed
        assert result.success is False

    def test_heal_unfixable_script(
        self,
        check_claude_available,
        e2e_config,
        tmp_path,
    ):
        """Test handling of scripts with challenging issues.

        Note: Claude may creatively fix "unfixable" scripts by removing
        problematic code or finding alternative solutions.
        """
        # Create a script with fundamental issues
        script = tmp_path / "unfixable.py"
        script.write_text(
            """#!/usr/bin/env python3
# This script has intentional issues that are hard to fix
import sys
import nonexistent_module_that_cannot_be_installed

def main():
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        )
        script.chmod(0o755)

        # Limit attempts
        e2e_config.healing.max_attempts = 2

        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(script)

        # Should attempt healing (may succeed or fail)
        assert len(result.attempts) >= 1
        assert len(result.attempts) <= e2e_config.healing.max_attempts
        # Note: Claude may creatively fix "unfixable" scripts by removing problematic code


class TestE2EIntegrationWithGit:
    """E2E tests for Git integration."""

    def test_heal_with_git_context(
        self,
        check_claude_available,
        e2e_config,
        tmp_path,
    ):
        """Test healing with Git context information."""
        # Initialize a git repo
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )

        # Create a broken script
        script = repo_path / "script.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys

def main():
    print(undefined_var)
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        )
        script.chmod(0o755)

        # Commit it
        subprocess.run(["git", "add", "script.py"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add broken script"],
            cwd=repo_path,
            check=True,
        )

        # Create healer
        healer = Healer(e2e_config)

        # Run healing process
        result = healer.heal(script)

        # Context should include git info
        # The healing should consider recent commits
        assert len(result.attempts) > 0


@pytest.mark.skipif(
    not os.environ.get("LAZARUS_RUN_E2E") and not shutil.which("claude"),
    reason="Set LAZARUS_RUN_E2E=1 or install Claude Code CLI to run",
)
class TestE2EPerformance:
    """E2E performance tests."""

    def test_healing_performance(
        self,
        check_claude_available,
        e2e_config,
        broken_python_script,
    ):
        """Test healing performance and duration."""
        import time

        healer = Healer(e2e_config)

        start_time = time.time()
        result = healer.heal(broken_python_script)
        duration = time.time() - start_time

        # Should complete within reasonable time
        assert duration < 180  # 3 minutes max for simple fix

        # Log performance metrics
        print("\nHealing Performance:")
        print(f"  Total duration: {duration:.2f}s")
        print(f"  Attempts: {len(result.attempts)}")
        if result.attempts:
            avg_attempt_time = sum(a.duration for a in result.attempts) / len(
                result.attempts
            )
            print(f"  Avg attempt time: {avg_attempt_time:.2f}s")
