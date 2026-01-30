# Claude Code Integration

This document describes the Claude Code integration for Lazarus, which enables automated script healing using Claude AI.

## Overview

The Claude Code integration consists of three main modules:

1. **client.py** - CLI wrapper for invoking Claude Code
2. **prompts.py** - Prompt templates and builders
3. **parser.py** - Output parsing and change detection

## Architecture

```
┌─────────────────────┐
│  HealingContext     │ (from core.context)
│  - script_path      │
│  - script_content   │
│  - execution_result │
│  - git_context      │
│  - system_context   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  build_healing_     │
│  prompt()           │ (prompts.py)
│                     │
│  Generates          │
│  structured prompt  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ClaudeCodeClient   │ (client.py)
│  .request_fix()     │
│                     │
│  Invokes claude CLI │
│  with subprocess    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  parse_claude_      │
│  output()           │ (parser.py)
│                     │
│  Extracts changes   │
│  and explanation    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ClaudeResponse     │
│  - success          │
│  - explanation      │
│  - files_changed    │
│  - error_message    │
└─────────────────────┘
```

## Usage

### Basic Usage

```python
from pathlib import Path
from lazarus.claude import ClaudeCodeClient
from lazarus.core.context import build_context

# Check if Claude Code is available
client = ClaudeCodeClient(working_dir=Path.cwd())
if not client.is_available():
    print("Claude Code CLI not found. Install with:")
    print("  npm install -g @anthropic-ai/claude-code")
    exit(1)

# Build healing context from a failed execution
context = build_context(
    script_path=Path("failing_script.py"),
    result=execution_result,
    config=lazarus_config,
)

# Request a fix
response = client.request_fix(context)

if response.success:
    print(f"Fixed! Changed files: {response.files_changed}")
    print(f"Explanation: {response.explanation}")
else:
    print(f"Failed: {response.error_message}")
```

### With Retry Logic

```python
# Request fix with automatic retries
response, attempts = client.request_fix_with_retry(
    context,
    max_attempts=3
)

print(f"Completed in {attempts} attempt(s)")
if response.success:
    print(f"Successfully fixed: {response.files_changed}")
```

### Custom Tool Restrictions

Configure which tools Claude Code can use:

```python
from lazarus.config.schema import HealingConfig, LazarusConfig

config = LazarusConfig(
    healing=HealingConfig(
        allowed_tools=["Edit", "Read"],  # Only allow reading and editing
        # OR
        forbidden_tools=["Bash"],  # Allow all except Bash
    )
)
```

## Prompt Structure

The healing prompts follow this structure:

```
# TASK
Fix the failing script at: /path/to/script.py

# ERROR INFORMATION
Exit Code: 1
Duration: 1.23s
Timestamp: 2024-01-30T12:00:00Z

## Standard Output:
...

## Standard Error:
...

# SCRIPT
File: /path/to/script.py
```
...
```

# GIT CONTEXT (if available)
Branch: main
Repository: /path/to/repo

## Recent Commits:
1. abc123 - Fix bug
   ...

## Uncommitted Changes:
```diff
...
```

# SYSTEM INFORMATION
OS: Darwin
OS Version: 23.0.0
Python: 3.11.0
Shell: /bin/bash
Working Directory: /path/to/dir

# INSTRUCTIONS
1. Analyze the error and identify the root cause
2. Make ONLY the minimal changes necessary to fix the issue
3. DO NOT refactor or improve unrelated code
...
```

## Output Parsing

The parser extracts information from Claude Code output using multiple strategies:

### File Change Detection

1. **Tool usage patterns**: `Edit[file_path="/path/to/file.py"]`
2. **Action descriptions**: "Edited file.py", "Modified script.py"
3. **Success messages**: "Successfully updated config.yaml"

### Explanation Extraction

1. **Direct statements**: "I've fixed the syntax error..."
2. **Issue descriptions**: "The issue was a missing import..."
3. **Fallback**: First substantial paragraph from output

### Error Detection

1. **Authentication errors**: "authentication failed", "not authenticated"
2. **Rate limits**: "rate limit exceeded", "too many requests"
3. **Generic errors**: Non-zero exit codes with stderr messages

## Error Handling

The integration handles several error scenarios:

- **CLI not installed**: Raises `RuntimeError` with installation instructions
- **Authentication failures**: Returns `ClaudeResponse` with auth error message
- **Rate limiting**: Returns `ClaudeResponse` indicating rate limit
- **Timeouts**: Returns `ClaudeResponse` after timeout (configurable, default 300s)
- **Subprocess errors**: Captures and returns error details

## Configuration

Claude Code integration is configured through `LazarusConfig`:

```yaml
healing:
  max_attempts: 3
  timeout_per_attempt: 300  # seconds
  total_timeout: 900
  claude_model: "claude-sonnet-4-5-20250929"
  max_turns: 30
  allowed_tools: []  # Empty = all tools allowed
  forbidden_tools: []

scripts:
  - name: my-script
    path: script.py
    allowed_files: ["script.py", "utils.py"]  # Only these can be modified
    forbidden_files: ["config.yaml"]  # Never modify these
    custom_prompt: "Additional context for Claude..."
    success_criteria:
      contains: "Success"  # Output must contain this
```

## Testing

The integration includes comprehensive unit tests:

- **test_claude_parser.py**: 12 tests for output parsing
- **test_claude_prompts.py**: 5 tests for prompt building
- **test_claude_client.py**: 15 tests for CLI client

Run tests:

```bash
pytest tests/unit/test_claude_*.py -v
```

## Dependencies

- **subprocess**: For invoking the Claude Code CLI
- **pathlib**: For file path handling
- **dataclasses**: For structured responses
- **typing**: For type hints

External:
- **Claude Code CLI**: Install via `npm install -g @anthropic-ai/claude-code`

## Security Considerations

1. **File access controls**: Use `allowed_files` and `forbidden_files` to restrict modifications
2. **Tool restrictions**: Limit available tools via `allowed_tools` or `forbidden_tools`
3. **Secret redaction**: Errors are redacted before sending to Claude (via security.redactor)
4. **Timeout enforcement**: Hard limits prevent runaway executions
5. **Subprocess isolation**: Commands run in specified working directory only

## Future Enhancements

- [ ] Streaming output support for long-running fixes
- [ ] Conversation context for multi-turn healing
- [ ] Parallel healing attempts with different strategies
- [ ] Cost tracking and budget limits
- [ ] Caching of successful fixes for similar errors
- [ ] Integration with other AI coding assistants
