# Context System Architecture

The Context System is the foundation of Lazarus's error capture and healing capabilities. It collects comprehensive information about script failures to enable Claude Code to effectively diagnose and fix issues.

## Overview

The Context System consists of three main components:

1. **Context Building** (`src/lazarus/core/context.py`) - Collects execution context
2. **Secrets Redaction** (`src/lazarus/security/redactor.py`) - Removes sensitive information
3. **Intelligent Truncation** (`src/lazarus/core/truncation.py`) - Fits context within token limits

## Components

### 1. Context Building

The context builder collects all relevant information about a script failure:

#### Data Structures

- **ExecutionResult**: Captures script execution outcomes
  - Exit code
  - stdout and stderr
  - Duration
  - Timestamp

- **GitContext**: Captures repository state
  - Current branch
  - Recent commits (last 5) with diffs
  - Uncommitted changes
  - Repository root path

- **SystemContext**: Captures system information
  - OS name and version
  - Python version
  - Shell
  - Current working directory

- **HealingContext**: Complete context for healing
  - Script path and content
  - Execution result
  - Git context (if available)
  - System context
  - Configuration

#### Functions

- `build_context()`: Main function to build complete healing context
- `get_git_context()`: Collects git repository information
- `get_system_context()`: Collects system and environment information

### 2. Secrets Redaction

The redactor protects sensitive information before sending context to Claude or logging it.

#### Features

- **Pattern-based Detection**: Uses configurable regex patterns to identify secrets
- **Default Patterns**: Built-in patterns for common secret types:
  - API keys
  - Tokens (Bearer, access tokens, etc.)
  - Passwords
  - AWS credentials
  - Private keys
  - Authorization headers

- **Custom Patterns**: Support for additional user-defined patterns
- **Safe Environment Variables**: Whitelist of variables safe to expose

#### Classes

- **Redactor**: Main class for redacting sensitive information
  - `from_config()`: Create redactor from Lazarus configuration
  - `redact()`: Redact text using configured patterns
  - `redact_dict()`: Redact dictionary values

#### Functions

- `redact_context()`: Redact complete healing context
- `redact_execution_result()`: Redact stdout/stderr
- `redact_git_context()`: Redact commit messages and diffs
- `filter_environment_variables()`: Filter env vars to safe list

### 3. Intelligent Truncation

The truncation system ensures context fits within LLM token limits while preserving the most important information.

#### Strategy

Information is prioritized as follows:

1. **Error output (stderr)** - 30% of tokens (highest priority)
2. **Script content** - 30% of tokens
3. **Git context** - 25% of tokens
4. **Standard output** - 15% of tokens

#### Features

- **Smart Truncation**: Removes least important information first
- **Position-aware**: Can truncate from start, end, or middle
- **Markers**: Adds `[TRUNCATED: X lines removed]` markers
- **Token Estimation**: Simple but effective character-based estimation

#### Functions

- `truncate_for_context()`: Main function for truncating healing context
- `truncate_text()`: Generic text truncation
- `truncate_execution_result()`: Truncate stdout/stderr (prioritizes stderr)
- `truncate_git_context()`: Truncate git information (prioritizes uncommitted changes)
- `estimate_tokens()`: Estimate token count (chars / 4)

## Usage Example

```python
from pathlib import Path
from lazarus.config.schema import LazarusConfig
from lazarus.core.context import ExecutionResult, build_context
from lazarus.security.redactor import redact_context
from lazarus.core.truncation import truncate_for_context

# Create execution result from failed script
result = ExecutionResult(
    exit_code=1,
    stdout="Connecting to database...",
    stderr="Error: Connection failed",
    duration=2.5
)

# Build complete context
config = LazarusConfig()
context = build_context(
    script_path=Path("/path/to/script.py"),
    result=result,
    config=config
)

# Redact sensitive information
safe_context = redact_context(context)

# Truncate to fit token limits
final_context = truncate_for_context(safe_context, max_tokens=100000)

# Now final_context is ready to send to Claude Code
```

## Security Considerations

The redaction system is designed to be conservative:

- **Patterns are broad**: May redact false positives to be safe
- **Whitelist approach**: Only explicitly safe environment variables are exposed
- **Multiple layers**: Redacts script content, output, and git history
- **User extensible**: Users can add custom patterns for their specific secrets

## Performance

- **Git operations**: Timeout after 5-10 seconds to prevent hanging
- **Subprocess safety**: All subprocess calls have timeouts
- **Memory efficient**: Streaming truncation where possible
- **Fast redaction**: Compiled regex patterns for performance

## Testing

The Context System has comprehensive test coverage (94%):

- **56 unit tests** covering all major functionality
- Tests for edge cases: missing git repos, file errors, timeouts
- Tests for security: verifies secrets are properly redacted
- Tests for truncation: verifies prioritization and limits

Run tests with:
```bash
PYTHONPATH=src python3 -m pytest tests/unit/ --cov
```

## Future Enhancements

Potential improvements for future versions:

1. **Smarter token estimation**: Use actual tokenizer instead of char/4 heuristic
2. **Semantic truncation**: Preserve complete logical blocks (functions, errors)
3. **Compression**: Compress less important context instead of removing it
4. **Caching**: Cache git context to avoid repeated subprocess calls
5. **Async operations**: Make git operations async for better performance
