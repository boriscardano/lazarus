"""Tests for Git operations module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lazarus.git.operations import GitOperationError, GitOperations


class TestGitOperations:
    """Test suite for GitOperations class."""

    @pytest.fixture
    def mock_repo_path(self, tmp_path: Path) -> Path:
        """Create a temporary directory that looks like a git repo."""
        return tmp_path

    @pytest.fixture
    def mock_git_command(self):
        """Mock subprocess.run for git commands."""
        with patch("lazarus.git.operations.subprocess.run") as mock_run:
            # Default successful response
            mock_run.return_value = Mock(
                returncode=0,
                stdout="",
                stderr="",
            )
            yield mock_run

    def test_init_valid_repo(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test initialization with valid git repository."""
        # Mock git rev-parse to return success
        mock_git_command.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        git_ops = GitOperations(mock_repo_path)

        assert git_ops.repo_path == mock_repo_path.resolve()
        mock_git_command.assert_called_once()

    def test_init_invalid_repo(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test initialization with non-git directory."""
        # Mock git rev-parse to return failure
        mock_git_command.return_value = Mock(returncode=128, stdout="", stderr="Not a git repository")

        with pytest.raises(ValueError, match="Not a git repository"):
            GitOperations(mock_repo_path)

    def test_get_current_branch(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting current branch name."""
        # Setup mock responses
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="feature-branch\n", stderr=""),  # get_current_branch
        ]

        git_ops = GitOperations(mock_repo_path)
        branch = git_ops.get_current_branch()

        assert branch == "feature-branch"

    def test_get_current_branch_detached_head(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting branch in detached HEAD state."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # get_current_branch (empty)
        ]

        git_ops = GitOperations(mock_repo_path)

        with pytest.raises(GitOperationError, match="Unable to determine current branch"):
            git_ops.get_current_branch()

    def test_has_uncommitted_changes_true(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test detecting uncommitted changes."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout=" M file.py\n", stderr=""),  # status --porcelain
        ]

        git_ops = GitOperations(mock_repo_path)
        has_changes = git_ops.has_uncommitted_changes()

        assert has_changes is True

    def test_has_uncommitted_changes_false(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test no uncommitted changes."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # status --porcelain (empty)
        ]

        git_ops = GitOperations(mock_repo_path)
        has_changes = git_ops.has_uncommitted_changes()

        assert has_changes is False

    def test_create_branch(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test creating a new branch."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # branch create
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.create_branch("new-feature")

        assert result is True
        # Check that git branch was called
        calls = mock_git_command.call_args_list
        assert any("branch" in str(call) and "new-feature" in str(call) for call in calls)

    def test_create_branch_failure(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test branch creation failure."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=128, stdout="", stderr="fatal: branch already exists"),  # branch create
        ]

        git_ops = GitOperations(mock_repo_path)

        with pytest.raises(GitOperationError, match="Git command failed"):
            git_ops.create_branch("existing-branch")

    def test_checkout_branch(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test checking out a branch."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="Switched to branch 'main'\n", stderr=""),  # checkout
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.checkout_branch("main")

        assert result is True

    def test_create_and_checkout_branch(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test creating and checking out a branch."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="Switched to a new branch 'feature'\n", stderr=""),  # checkout -b
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.create_and_checkout_branch("feature")

        assert result is True

    def test_add_files(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test staging files."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="", stderr=""),  # git add
        ]

        git_ops = GitOperations(mock_repo_path)
        files = [Path("file1.py"), Path("file2.py")]
        result = git_ops.add_files(files)

        assert result is True

    def test_add_files_empty_list(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test staging empty file list."""
        mock_git_command.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.add_files([])

        assert result is True

    def test_commit(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test creating a commit."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="[main abc123] Test commit\n", stderr=""),  # commit
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.commit("Test commit message")

        assert result is True

    def test_commit_empty_message(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test commit with empty message raises error."""
        mock_git_command.return_value = Mock(returncode=0, stdout=".git\n", stderr="")

        git_ops = GitOperations(mock_repo_path)

        with pytest.raises(ValueError, match="Commit message cannot be empty"):
            git_ops.commit("")

    def test_push(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test pushing to remote."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="main\n", stderr=""),  # get_current_branch
            Mock(returncode=0, stdout="", stderr=""),  # push
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.push()

        assert result is True

    def test_push_with_upstream(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test pushing with set-upstream."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="feature\n", stderr=""),  # get_current_branch
            Mock(returncode=0, stdout="", stderr=""),  # push
        ]

        git_ops = GitOperations(mock_repo_path)
        result = git_ops.push(branch="feature", set_upstream=True)

        assert result is True

    def test_get_default_branch_from_remote(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting default branch from remote."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="refs/remotes/origin/main\n", stderr=""),  # symbolic-ref
        ]

        git_ops = GitOperations(mock_repo_path)
        branch = git_ops.get_default_branch()

        assert branch == "main"

    def test_get_default_branch_fallback(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting default branch with fallback."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=128, stdout="", stderr=""),  # symbolic-ref (fails)
            Mock(returncode=0, stdout="", stderr=""),  # rev-parse main
        ]

        git_ops = GitOperations(mock_repo_path)
        branch = git_ops.get_default_branch()

        assert branch == "main"

    def test_branch_exists_true(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test checking if branch exists."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="abc123\n", stderr=""),  # rev-parse
        ]

        git_ops = GitOperations(mock_repo_path)
        exists = git_ops.branch_exists("feature")

        assert exists is True

    def test_branch_exists_false(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test checking if branch doesn't exist."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=128, stdout="", stderr="fatal: bad revision"),  # rev-parse
        ]

        git_ops = GitOperations(mock_repo_path)
        exists = git_ops.branch_exists("nonexistent")

        assert exists is False

    def test_get_remote_url(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting remote URL."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=0, stdout="https://github.com/user/repo.git\n", stderr=""),  # remote get-url
        ]

        git_ops = GitOperations(mock_repo_path)
        url = git_ops.get_remote_url()

        assert url == "https://github.com/user/repo.git"

    def test_get_remote_url_not_found(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test getting remote URL when remote doesn't exist."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            Mock(returncode=128, stdout="", stderr="fatal: No such remote"),  # remote get-url
        ]

        git_ops = GitOperations(mock_repo_path)
        url = git_ops.get_remote_url("nonexistent")

        assert url is None

    def test_command_timeout(self, mock_repo_path: Path, mock_git_command: Mock):
        """Test git command timeout."""
        mock_git_command.side_effect = [
            Mock(returncode=0, stdout=".git\n", stderr=""),  # is_git_repo check
            subprocess.TimeoutExpired("git", 30),  # timeout on next command
        ]

        git_ops = GitOperations(mock_repo_path)

        with pytest.raises(GitOperationError, match="timed out"):
            git_ops.get_current_branch()
