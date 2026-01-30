#!/usr/bin/env python3
"""Example demonstrating the PR creation workflow in Lazarus.

This example shows how to use GitOperations and PRCreator to:
1. Check git repository state
2. Create branches
3. Create pull requests after healing

Note: This is a demonstration. In practice, PR creation is automatic
after successful healing when git.create_pr=True in config.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lazarus.claude.parser import ClaudeResponse
from lazarus.config.schema import GitConfig
from lazarus.core.context import ExecutionResult
from lazarus.core.healer import HealingAttempt, HealingResult
from lazarus.core.verification import VerificationResult
from lazarus.git.operations import GitOperationError, GitOperations
from lazarus.git.pr import PRCreator


def demonstrate_git_operations():
    """Demonstrate basic git operations."""
    print("=" * 60)
    print("Git Operations Demo")
    print("=" * 60)

    try:
        # Initialize GitOperations
        repo_path = Path.cwd()
        git_ops = GitOperations(repo_path)

        print(f"\n1. Repository: {repo_path}")

        # Get current branch
        current_branch = git_ops.get_current_branch()
        print(f"2. Current branch: {current_branch}")

        # Get default branch
        default_branch = git_ops.get_default_branch()
        print(f"3. Default branch: {default_branch}")

        # Check for uncommitted changes
        has_changes = git_ops.has_uncommitted_changes()
        print(f"4. Uncommitted changes: {'Yes' if has_changes else 'No'}")

        # Get remote URL
        remote_url = git_ops.get_remote_url()
        print(f"5. Remote URL: {remote_url or 'Not configured'}")

        print("\n✅ Git operations working correctly!")

    except GitOperationError as e:
        print(f"\n❌ Git operation failed: {e}")
    except ValueError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


def demonstrate_pr_creation():
    """Demonstrate PR creation (dry-run mode)."""
    print("\n" + "=" * 60)
    print("PR Creation Demo (Check Prerequisites)")
    print("=" * 60)

    try:
        # Create a sample GitConfig
        config = GitConfig(
            create_pr=True,
            branch_prefix="lazarus/fix",
            draft_pr=False,
        )

        # Initialize PRCreator
        repo_path = Path.cwd()
        pr_creator = PRCreator(config, repo_path)

        print("\n1. Checking GitHub CLI availability...")
        gh_available = pr_creator.is_gh_available()
        print(f"   GitHub CLI (gh): {'✅ Installed' if gh_available else '❌ Not installed'}")

        if gh_available:
            print("\n2. Checking GitHub authentication...")
            gh_auth = pr_creator.is_gh_authenticated()
            print(f"   Authentication: {'✅ Authenticated' if gh_auth else '❌ Not authenticated'}")

            if not gh_auth:
                print("\n   To authenticate, run: gh auth login")

        # Create a sample healing result for demonstration
        sample_script = Path("scripts/example.py")

        print(f"\n3. Sample PR title for {sample_script}:")
        title = pr_creator.build_pr_title(sample_script)
        print(f"   {title}")

        # Create a mock healing result
        mock_execution = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ImportError: No module named 'requests'",
            duration=0.1,
            timestamp="2024-01-30T12:00:00",
            success=False,
        )

        mock_claude_response = ClaudeResponse(
            success=True,
            modified_files=[],
            error_message=None,
            execution_output=None,
        )

        mock_verification = VerificationResult(
            status="success",
            execution_result=mock_execution,
        )

        mock_attempt = HealingAttempt(
            attempt_number=1,
            claude_response=mock_claude_response,
            verification=mock_verification,
            duration=5.0,
        )

        mock_healing = HealingResult(
            success=True,
            attempts=[mock_attempt],
            final_execution=mock_execution,
            duration=10.0,
        )

        print("\n4. Sample PR body (first 500 chars):")
        body = pr_creator.build_pr_body(mock_healing, sample_script)
        print("-" * 60)
        print(body[:500] + "...")
        print("-" * 60)

        if gh_available and gh_auth:
            print("\n✅ All prerequisites met for PR creation!")
            print("\nNote: Actual PR creation would happen automatically")
            print("      when healing succeeds with git.create_pr=True")
        else:
            print("\n⚠️  Setup required before PR creation:")
            if not gh_available:
                print("   - Install GitHub CLI: https://cli.github.com/")
            if not gh_auth:
                print("   - Authenticate: gh auth login")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Run all demonstrations."""
    print("\n🔧 Lazarus PR Creation System Demo")
    print("This demonstrates git operations and PR creation capabilities.\n")

    demonstrate_git_operations()
    demonstrate_pr_creation()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nFor more information:")
    print("  - docs/git-integration.md")
    print("  - docs/configuration.md")
    print()


if __name__ == "__main__":
    main()
