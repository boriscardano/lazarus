"""Core healing functionality.

Note: Healer, HealingAttempt, and HealingResult are imported directly from
lazarus.core.healer to avoid circular imports with the claude module.
"""

from lazarus.core.context import (
    CommitInfo,
    ExecutionResult,
    GitContext,
    HealingContext,
    SystemContext,
    build_context,
    get_git_context,
    get_system_context,
)
from lazarus.core.loop import HealingLoop
from lazarus.core.runner import ScriptRunner
from lazarus.core.verification import (
    ErrorComparison,
    VerificationResult,
    check_custom_criteria,
    compare_errors,
)

__all__ = [
    # Context
    "ExecutionResult",
    "CommitInfo",
    "GitContext",
    "SystemContext",
    "HealingContext",
    "build_context",
    "get_git_context",
    "get_system_context",
    # Loop
    "HealingLoop",
    # Runner
    "ScriptRunner",
    # Verification
    "ErrorComparison",
    "VerificationResult",
    "compare_errors",
    "check_custom_criteria",
]
