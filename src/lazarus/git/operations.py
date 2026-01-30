"""Git operations for Lazarus.

This module provides a GitOperations class that wraps common git commands
using subprocess. It handles branch management, committing, pushing, and
repository state queries with proper error handling and logging.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when a git operation fails."""

    pass


class GitOperations:
    """Git operations wrapper using subprocess.

    This class provides a clean interface for common git operations needed
    by Lazarus, including branch management, committing, and pushing changes.

    Attributes:
        repo_path: Path to the git repository
    """

    def __init__(self, repo_path: Path) -> None:
        """Initialize GitOperations.

        Args:
            repo_path: Path to the git repository root

        Raises:
            ValueError: If repo_path is not a valid git repository
        """
        self.repo_path = repo_path.resolve()

        # Verify this is a git repository
        if not self._is_git_repo():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository.

        Returns:
            True if repo_path is a valid git repository
        """
        try:
            result = self._run_git_command(
                ["rev-parse", "--git-dir"],
                check=False,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def _run_git_command(
        self,
        args: list[str],
        check: bool = True,
        capture_output: bool = True,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repository.

        Args:
            args: Git command arguments (without 'git' prefix)
            check: Whether to raise exception on non-zero exit
            capture_output: Whether to capture stdout/stderr
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess with command results

        Raises:
            GitOperationError: If command fails and check=True
        """
        cmd = ["git"] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False,
                timeout=timeout,
            )

            if check and result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(
                    "Git command failed: %s (exit code %d): %s",
                    " ".join(cmd),
                    result.returncode,
                    error_msg,
                )
                raise GitOperationError(
                    f"Git command failed: {' '.join(cmd)}: {error_msg}"
                )

            return result

        except subprocess.TimeoutExpired as e:
            logger.error("Git command timed out: %s", " ".join(cmd))
            raise GitOperationError(f"Git command timed out: {' '.join(cmd)}") from e
        except OSError as e:
            logger.error("Failed to execute git command: %s: %s", " ".join(cmd), e)
            raise GitOperationError(f"Failed to execute git: {e}") from e

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name

        Raises:
            GitOperationError: If unable to determine current branch
        """
        result = self._run_git_command(["branch", "--show-current"])
        branch = result.stdout.strip()

        if not branch:
            # Might be in detached HEAD state
            logger.warning("Unable to determine current branch (detached HEAD?)")
            raise GitOperationError("Unable to determine current branch")

        logger.debug("Current branch: %s", branch)
        return branch

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes in the repository.

        This includes both staged and unstaged changes, as well as untracked files.

        Returns:
            True if there are uncommitted changes
        """
        result = self._run_git_command(["status", "--porcelain"])
        has_changes = bool(result.stdout.strip())

        logger.debug("Uncommitted changes: %s", "yes" if has_changes else "no")
        return has_changes

    def create_branch(self, branch_name: str) -> bool:
        """Create a new branch.

        Args:
            branch_name: Name of the branch to create

        Returns:
            True if branch was created successfully

        Raises:
            GitOperationError: If branch creation fails
        """
        logger.info("Creating branch: %s", branch_name)

        try:
            self._run_git_command(["branch", branch_name])
            logger.info("Branch created successfully: %s", branch_name)
            return True
        except GitOperationError as e:
            logger.error("Failed to create branch %s: %s", branch_name, e)
            raise

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout an existing branch.

        Args:
            branch_name: Name of the branch to checkout

        Returns:
            True if checkout was successful

        Raises:
            GitOperationError: If checkout fails
        """
        logger.info("Checking out branch: %s", branch_name)

        try:
            self._run_git_command(["checkout", branch_name])
            logger.info("Checked out branch: %s", branch_name)
            return True
        except GitOperationError as e:
            logger.error("Failed to checkout branch %s: %s", branch_name, e)
            raise

    def create_and_checkout_branch(self, branch_name: str) -> bool:
        """Create and checkout a new branch in one operation.

        Args:
            branch_name: Name of the branch to create and checkout

        Returns:
            True if operation was successful

        Raises:
            GitOperationError: If operation fails
        """
        logger.info("Creating and checking out branch: %s", branch_name)

        try:
            self._run_git_command(["checkout", "-b", branch_name])
            logger.info("Created and checked out branch: %s", branch_name)
            return True
        except GitOperationError as e:
            logger.error("Failed to create/checkout branch %s: %s", branch_name, e)
            raise

    def add_files(self, files: list[Path]) -> bool:
        """Stage files for commit.

        Args:
            files: List of file paths to stage (can be relative to repo_path)

        Returns:
            True if files were staged successfully

        Raises:
            GitOperationError: If staging fails
        """
        if not files:
            logger.warning("No files to add")
            return True

        # Convert paths to strings relative to repo_path
        file_strs = [str(f) for f in files]

        logger.info("Staging %d file(s)", len(files))
        logger.debug("Files to stage: %s", ", ".join(file_strs))

        try:
            self._run_git_command(["add"] + file_strs)
            logger.info("Files staged successfully")
            return True
        except GitOperationError as e:
            logger.error("Failed to stage files: %s", e)
            raise

    def commit(self, message: str) -> bool:
        """Create a commit with the staged changes.

        Args:
            message: Commit message

        Returns:
            True if commit was created successfully

        Raises:
            GitOperationError: If commit fails
        """
        if not message:
            raise ValueError("Commit message cannot be empty")

        logger.info("Creating commit")
        logger.debug("Commit message: %s", message[:100])  # Log first 100 chars

        try:
            self._run_git_command(["commit", "-m", message])
            logger.info("Commit created successfully")
            return True
        except GitOperationError as e:
            logger.error("Failed to create commit: %s", e)
            raise

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
    ) -> bool:
        """Push commits to remote repository.

        Args:
            remote: Remote name (default: "origin")
            branch: Branch name to push (default: current branch)
            set_upstream: Set upstream tracking (default: False)

        Returns:
            True if push was successful

        Raises:
            GitOperationError: If push fails
        """
        if branch is None:
            branch = self.get_current_branch()

        logger.info("Pushing to %s/%s", remote, branch)

        cmd_args = ["push"]
        if set_upstream:
            cmd_args.extend(["--set-upstream", remote, branch])
        else:
            cmd_args.extend([remote, branch])

        try:
            self._run_git_command(cmd_args, timeout=120)  # Longer timeout for push
            logger.info("Push successful")
            return True
        except GitOperationError as e:
            logger.error("Failed to push: %s", e)
            raise

    def get_default_branch(self) -> str:
        """Detect the default branch (main or master).

        This checks for common default branch names in order of preference.

        Returns:
            Name of the default branch

        Raises:
            GitOperationError: If unable to determine default branch
        """
        # Try to get default branch from remote
        try:
            result = self._run_git_command(
                ["symbolic-ref", "refs/remotes/origin/HEAD"],
                check=False,
            )
            if result.returncode == 0:
                # Output looks like: refs/remotes/origin/main
                branch = result.stdout.strip().split("/")[-1]
                logger.debug("Default branch from remote: %s", branch)
                return branch
        except GitOperationError:
            pass

        # Fall back to checking for common branch names
        for branch_name in ["main", "master", "develop"]:
            result = self._run_git_command(
                ["rev-parse", "--verify", branch_name],
                check=False,
            )
            if result.returncode == 0:
                logger.debug("Default branch (fallback): %s", branch_name)
                return branch_name

        # Last resort: use current branch
        logger.warning("Unable to determine default branch, using current branch")
        return self.get_current_branch()

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.

        Args:
            branch_name: Name of the branch to check

        Returns:
            True if branch exists
        """
        result = self._run_git_command(
            ["rev-parse", "--verify", branch_name],
            check=False,
        )
        exists = result.returncode == 0
        logger.debug("Branch %s exists: %s", branch_name, exists)
        return exists

    def get_remote_url(self, remote: str = "origin") -> str | None:
        """Get the URL of a remote.

        Args:
            remote: Remote name (default: "origin")

        Returns:
            Remote URL or None if remote doesn't exist
        """
        result = self._run_git_command(
            ["remote", "get-url", remote],
            check=False,
        )

        if result.returncode == 0:
            url = result.stdout.strip()
            logger.debug("Remote %s URL: %s", remote, url)
            return url

        logger.debug("Remote %s not found", remote)
        return None

    def stash_changes(self, message: str | None = None) -> bool:
        """Stash uncommitted changes.

        Args:
            message: Optional message for the stash

        Returns:
            True if changes were stashed successfully

        Raises:
            GitOperationError: If stash fails
        """
        logger.info("Stashing uncommitted changes")

        cmd_args = ["stash", "push"]
        if message:
            cmd_args.extend(["-m", message])

        try:
            self._run_git_command(cmd_args)
            logger.info("Changes stashed successfully")
            return True
        except GitOperationError as e:
            logger.error("Failed to stash changes: %s", e)
            raise

    def pop_stash(self) -> bool:
        """Pop the most recent stash.

        Returns:
            True if stash was popped successfully

        Raises:
            GitOperationError: If pop fails
        """
        logger.info("Popping stashed changes")

        try:
            self._run_git_command(["stash", "pop"])
            logger.info("Stash popped successfully")
            return True
        except GitOperationError as e:
            logger.error("Failed to pop stash: %s", e)
            raise

    def has_stash(self) -> bool:
        """Check if there are any stashed changes.

        Returns:
            True if there are stashed changes
        """
        result = self._run_git_command(["stash", "list"], check=False)
        has_stash = bool(result.stdout.strip())
        logger.debug("Has stash: %s", has_stash)
        return has_stash
