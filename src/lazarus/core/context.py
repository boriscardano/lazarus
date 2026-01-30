"""Context builder for capturing execution context and error information.

This module provides data structures and functions to collect comprehensive
context about script failures, including execution results, git state, system
information, and more.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lazarus.config.schema import LazarusConfig


@dataclass
class ExecutionResult:
    """Result from executing a script.

    Attributes:
        exit_code: Process exit code
        stdout: Standard output from the script
        stderr: Standard error from the script
        duration: Execution time in seconds
        timestamp: When the execution completed (UTC)
    """
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0


@dataclass
class CommitInfo:
    """Information about a single git commit.

    Attributes:
        hash: Commit SHA hash
        author: Commit author
        date: Commit date
        message: Commit message
        diff: Diff of changes in this commit (optional)
    """
    hash: str
    author: str
    date: str
    message: str
    diff: Optional[str] = None


@dataclass
class GitContext:
    """Git repository context.

    Attributes:
        branch: Current branch name
        recent_commits: Last 5 commits with their information
        uncommitted_changes: Diff of uncommitted changes
        repo_root: Root directory of the git repository
    """
    branch: str
    recent_commits: list[CommitInfo]
    uncommitted_changes: str
    repo_root: Path


@dataclass
class SystemContext:
    """System and environment context.

    Attributes:
        os_name: Operating system name (e.g., 'Linux', 'Darwin', 'Windows')
        os_version: Operating system version
        python_version: Python version string
        shell: Shell being used
        cwd: Current working directory
    """
    os_name: str
    os_version: str
    python_version: str
    shell: str
    cwd: Path


@dataclass
class PreviousAttempt:
    """Record of a previous healing attempt.

    This tracks what Claude tried before so it can avoid repeating the same
    unsuccessful approaches.

    Attributes:
        attempt_number: The attempt number (1-indexed)
        claude_response_summary: Brief summary of what Claude tried to fix
        changes_made: List of files that were changed
        error_after: The error message after this attempt failed
    """
    attempt_number: int
    claude_response_summary: str
    changes_made: list[str]
    error_after: str


@dataclass
class HealingContext:
    """Complete context for healing a failed script.

    This contains all information needed to understand and fix a script failure,
    including the script itself, execution results, git state, and system info.

    Attributes:
        script_path: Path to the script that failed
        script_content: Content of the script file
        execution_result: Results from the failed execution
        git_context: Git repository state (if in a git repo)
        system_context: System and environment information
        config: Lazarus configuration for this script
        previous_attempts: List of previous healing attempts that failed
    """
    script_path: Path
    script_content: str
    execution_result: ExecutionResult
    git_context: Optional[GitContext]
    system_context: SystemContext
    config: LazarusConfig
    previous_attempts: list[PreviousAttempt] = field(default_factory=list)


def get_git_context(repo_path: Path) -> Optional[GitContext]:
    """Collect git context from a repository.

    Args:
        repo_path: Path to check for git repository (searches up from here)

    Returns:
        GitContext if in a git repository, None otherwise
    """
    try:
        # Find git root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        repo_root = Path(result.stdout.strip())

        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        branch = result.stdout.strip()

        # Get last 5 commits with details
        recent_commits: list[CommitInfo] = []
        result = subprocess.run(
            [
                "git",
                "log",
                "-5",
                "--format=%H%n%an%n%ad%n%s%n---COMMIT-END---",
                "--date=iso",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            commits_raw = result.stdout.strip().split("---COMMIT-END---")
            for commit_raw in commits_raw:
                lines = commit_raw.strip().split("\n")
                if len(lines) >= 4:
                    commit_hash = lines[0]
                    author = lines[1]
                    date = lines[2]
                    message = lines[3]

                    # Get diff for this commit (only show changed files, not full diff)
                    diff_result = subprocess.run(
                        ["git", "show", "--stat", commit_hash],
                        cwd=repo_root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    diff = diff_result.stdout if diff_result.returncode == 0 else None

                    recent_commits.append(
                        CommitInfo(
                            hash=commit_hash,
                            author=author,
                            date=date,
                            message=message,
                            diff=diff,
                        )
                    )

        # Get uncommitted changes
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        uncommitted_changes = result.stdout if result.returncode == 0 else ""

        # Also check for untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            untracked = result.stdout.strip().split("\n")
            if untracked:
                uncommitted_changes += f"\n\n# Untracked files:\n"
                for file in untracked:
                    uncommitted_changes += f"# {file}\n"

        return GitContext(
            branch=branch,
            recent_commits=recent_commits,
            uncommitted_changes=uncommitted_changes,
            repo_root=repo_root,
        )

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None


def get_system_context() -> SystemContext:
    """Collect system and environment context.

    Returns:
        SystemContext with current system information
    """
    # Get OS information
    os_name = platform.system()
    os_version = platform.version()

    # Get Python version
    python_version = sys.version

    # Get shell
    shell = os.environ.get("SHELL") or "unknown"

    # Get current working directory
    cwd = Path.cwd()

    return SystemContext(
        os_name=os_name,
        os_version=os_version,
        python_version=python_version,
        shell=shell,
        cwd=cwd,
    )


def build_context(
    script_path: Path,
    result: ExecutionResult,
    config: LazarusConfig,
) -> HealingContext:
    """Build complete healing context for a failed script execution.

    This function collects all relevant information about a script failure:
    - Reads the script file content
    - Collects git context if available
    - Collects system context
    - Packages everything with the execution result

    Args:
        script_path: Path to the script that failed
        result: Execution result from running the script
        config: Lazarus configuration

    Returns:
        HealingContext with all collected information

    Raises:
        FileNotFoundError: If script_path does not exist
        PermissionError: If script_path cannot be read
    """
    # Read script content
    script_content = script_path.read_text(encoding="utf-8")

    # Get git context (if in a git repo)
    git_context = get_git_context(script_path.parent)

    # Get system context
    system_context = get_system_context()

    return HealingContext(
        script_path=script_path,
        script_content=script_content,
        execution_result=result,
        git_context=git_context,
        system_context=system_context,
        config=config,
    )
