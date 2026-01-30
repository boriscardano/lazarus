"""Claude Code integration.

This package provides integration with Claude Code CLI for automated script
healing. It includes:
- ClaudeCodeClient: CLI wrapper for invoking Claude Code
- Prompt building utilities for structured healing requests
- Output parsing for extracting results and file changes
"""

from lazarus.claude.client import ClaudeCodeClient
from lazarus.claude.parser import ClaudeResponse, parse_claude_output
from lazarus.claude.prompts import build_healing_prompt, build_retry_prompt

__all__ = [
    "ClaudeCodeClient",
    "ClaudeResponse",
    "parse_claude_output",
    "build_healing_prompt",
    "build_retry_prompt",
]
