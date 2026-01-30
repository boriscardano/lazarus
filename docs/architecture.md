# Architecture

System architecture and design overview for Lazarus.

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [Component Diagram](#component-diagram)
- [Data Flow](#data-flow)
- [Core Components](#core-components)
- [Integration Points](#integration-points)
- [Module Responsibilities](#module-responsibilities)
- [Design Principles](#design-principles)
- [Extension Points](#extension-points)

---

## High-Level Overview

Lazarus is a self-healing script runner that automatically detects, diagnoses, and fixes failing scripts using AI. It orchestrates the Claude Code CLI to execute automated code changes with verification and pull request creation.

### System Goals

- **Automated Healing**: Detect and fix script failures without human intervention
- **Safety First**: Comprehensive secrets redaction and verification before changes
- **Developer Friendly**: Beautiful CLI output and comprehensive logging
- **Production Ready**: Robust error handling, timeouts, and retry logic
- **Extensible**: Plugin architecture for notifications and custom verifications

### Key Architectural Decisions

1. **CLI-First Design**: Subprocess calls to `claude` CLI rather than direct API integration
2. **Configuration as Code**: YAML-based configuration with Pydantic validation
3. **Stateless Execution**: Each healing session is independent (state in git only)
4. **Modular Components**: Clear separation of concerns between modules
5. **Type Safety**: Full type hints throughout the codebase (mypy strict mode)

---

## Component Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                      Lazarus CLI (Typer)                          │
│                                                                   │
│  Commands: heal, run, history, validate, init, check             │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ├─────────────────────────────────────────────────┐
                │                                                 │
┌───────────────▼──────────────┐                  ┌──────────────▼──────────┐
│   Configuration System       │                  │    Healer (Core)        │
│                              │                  │                         │
│ • ConfigLoader               │                  │ • Orchestrates healing  │
│ • Pydantic Schema            │                  │ • Manages retry loop    │
│ • YAML Parser                │                  │ • Coordinates modules   │
│ • Validator                  │                  │                         │
└──────────────┬───────────────┘                  └─────────┬───────────────┘
               │                                            │
               │                                            │
               │        ┌───────────────────────────────────┴───────┐
               │        │                                           │
               │   ┌────▼────────────┐                  ┌──────────▼────────┐
               │   │  Context        │                  │  Claude Code      │
               │   │  Builder        │                  │  Client           │
               │   │                 │                  │                   │
               │   │ • Execution     │                  │ • Subprocess mgmt │
               │   │ • Git context   │                  │ • Prompt building │
               │   │ • System info   │                  │ • Output parsing  │
               │   │ • Redaction     │                  │                   │
               │   └────┬────────────┘                  └──────────┬────────┘
               │        │                                          │
               │        │                                          │
               │   ┌────▼────────────┐                  ┌──────────▼────────┐
               │   │  Security       │                  │  Verification     │
               │   │  (Redactor)     │                  │  Engine           │
               │   │                 │                  │                   │
               │   │ • Pattern       │                  │ • Script runner   │
               │   │   matching      │                  │ • Exit code check │
               │   │ • Secrets       │                  │ • Output compare  │
               │   │   redaction     │                  │                   │
               │   └─────────────────┘                  └──────────┬────────┘
               │                                                   │
               └───────────────────────┬───────────────────────────┘
                                       │
                   ┌───────────────────┴──────────────────┐
                   │                                      │
          ┌────────▼────────┐                  ┌─────────▼──────────┐
          │  Git/PR         │                  │  Notifications     │
          │  Operations     │                  │  Dispatcher        │
          │                 │                  │                    │
          │ • Branch mgmt   │                  │ • Slack            │
          │ • Commit        │                  │ • Discord          │
          │ • PR creation   │                  │ • Email            │
          │ • gh CLI        │                  │ • GitHub Issues    │
          │                 │                  │ • Webhooks         │
          └─────────────────┘                  └────────────────────┘
                   │                                      │
                   │                                      │
          ┌────────▼────────┐                  ┌─────────▼──────────┐
          │  Logging &      │                  │  History           │
          │  Formatting     │                  │  Manager           │
          │                 │                  │                    │
          │ • Rich output   │                  │ • JSON storage     │
          │ • Structured    │                  │ • Query interface  │
          │   logging       │                  │ • Record keeping   │
          │ • Progress      │                  │                    │
          └─────────────────┘                  └────────────────────┘
```

---

## Data Flow

### Healing Process Flow

```
1. User invokes CLI
   │
   ├─> Load Configuration
   │   └─> Validate schema
   │
   ├─> Run Script
   │   ├─> Capture stdout/stderr
   │   ├─> Record exit code
   │   └─> Measure duration
   │
   ├─> Check if script succeeded
   │   ├─> Yes: Exit with success
   │   └─> No: Continue to healing
   │
   ├─> Build Healing Context
   │   ├─> Script content
   │   ├─> Execution result
   │   ├─> Git context (commits, diffs)
   │   ├─> System context (OS, shell, etc)
   │   └─> Apply redaction
   │
   ├─> Healing Loop (up to max_attempts)
   │   │
   │   ├─> Request Fix from Claude Code
   │   │   ├─> Build prompt
   │   │   ├─> Execute subprocess
   │   │   └─> Parse output
   │   │
   │   ├─> Verify Fix
   │   │   ├─> Re-run script
   │   │   ├─> Compare results
   │   │   └─> Determine status
   │   │
   │   ├─> Check status
   │   │   ├─> Success: Exit loop
   │   │   ├─> Same error: Enhance context, retry
   │   │   ├─> Different error: Update context, retry
   │   │   └─> Timeout: Enhance context, retry
   │   │
   │   └─> Loop continues or exits
   │
   ├─> Create Pull Request (if enabled)
   │   ├─> Create branch
   │   ├─> Commit changes
   │   ├─> Push to remote
   │   └─> Create PR via gh CLI
   │
   ├─> Send Notifications
   │   ├─> Format message
   │   ├─> Dispatch to channels
   │   └─> Handle errors
   │
   └─> Log Results
       ├─> Write history record
       ├─> Display summary
       └─> Exit with appropriate code
```

### Context Building Flow

```
ExecutionResult + ScriptPath + Config
   │
   ├─> Read script content
   │
   ├─> Build Git context
   │   ├─> Get recent commits (git log)
   │   ├─> Get uncommitted changes (git diff)
   │   └─> Get current branch
   │
   ├─> Build System context
   │   ├─> OS information
   │   ├─> Shell information
   │   └─> Environment variables
   │
   ├─> Create HealingContext
   │
   └─> Apply Redaction
       ├─> Redact script content
       ├─> Redact execution output
       ├─> Redact git commits/diffs
       └─> Filter environment variables
```

---

## Core Components

### 1. CLI Interface (`cli.py`)

**Purpose**: User-facing command-line interface built with Typer and Rich.

**Responsibilities**:
- Command parsing and validation
- Configuration loading and override
- Progress display and user feedback
- Error handling and exit codes
- Rich terminal output (tables, panels, progress bars)

**Key Commands**:
- `heal` - Heal a specific failing script
- `run` - Run script with automatic healing
- `history` - View healing history
- `validate` - Validate configuration
- `init` - Create configuration template
- `check` - Verify prerequisites

### 2. Configuration System (`config/`)

**Purpose**: YAML configuration parsing and validation using Pydantic v2.

**Components**:
- `schema.py` - Pydantic models with validation rules
- `loader.py` - Configuration file discovery and loading

**Key Models**:
- `LazarusConfig` - Root configuration
- `ScriptConfig` - Script-specific settings
- `HealingConfig` - Healing behavior settings
- `NotificationConfig` - Notification channels
- `GitConfig` - Git/PR settings
- `SecurityConfig` - Secrets redaction patterns
- `LoggingConfig` - Logging behavior

**Validation Features**:
- Type checking and coercion
- Range validation (min/max)
- Pattern validation (regex)
- Cross-field validation (e.g., total_timeout ≥ timeout_per_attempt)
- Enum validation for restricted values

### 3. Healer (`core/healer.py`)

**Purpose**: Main orchestrator for the healing process.

**Responsibilities**:
- Script execution and failure detection
- Healing loop management with retry logic
- Context building and enhancement
- Claude Code client coordination
- Result aggregation and reporting

**Key Classes**:
- `Healer` - Main orchestration class
- `HealingResult` - Complete result with all attempts
- `HealingAttempt` - Single attempt record

**Workflow**:
1. Run script to capture failure
2. Build comprehensive context
3. Loop through healing attempts
4. Verify each fix by re-running
5. Return complete result

### 4. Context Builder (`core/context.py`)

**Purpose**: Build comprehensive context for Claude Code.

**Context Components**:
- **ExecutionResult**: stdout, stderr, exit code, duration
- **GitContext**: recent commits, uncommitted changes, branch
- **SystemContext**: OS, shell, environment variables
- **ScriptContent**: Full script source code

**Key Functions**:
- `build_context()` - Create complete HealingContext
- `build_execution_result()` - Capture script execution
- `build_git_context()` - Extract git information
- `build_system_context()` - Gather system information

### 5. Security Redactor (`security/redactor.py`)

**Purpose**: Detect and redact sensitive information before sending to AI.

**Redaction Patterns**:
- API keys and tokens
- Passwords and secrets
- AWS credentials
- Private keys and certificates
- Bearer tokens and auth headers

**Key Classes**:
- `Redactor` - Pattern-based redaction engine
- Helper functions for different context types

**Features**:
- Regex-based pattern matching
- Configurable patterns
- Context-aware redaction
- Environment variable filtering

### 6. Claude Code Client (`claude/client.py`)

**Purpose**: Subprocess wrapper for Claude Code CLI.

**Responsibilities**:
- Claude Code availability checking
- Subprocess management with timeouts
- Tool restriction enforcement
- Output parsing and error handling

**Key Classes**:
- `ClaudeCodeClient` - Main client class

**Methods**:
- `is_available()` - Check if claude CLI exists
- `get_version()` - Get Claude Code version
- `request_fix()` - Request healing from Claude
- `_get_allowed_tools()` - Determine tool restrictions

### 7. Prompt Builder (`claude/prompts.py`)

**Purpose**: Build structured prompts for Claude Code.

**Prompt Structure**:
1. Problem statement
2. Script information
3. Execution context
4. Error details
5. Git context
6. System environment
7. Healing instructions

**Functions**:
- `build_healing_prompt()` - Create comprehensive prompt
- Helper functions for formatting context sections

### 8. Verification Engine (`core/verification.py`)

**Purpose**: Verify that fixes actually work.

**Verification Process**:
1. Re-run script with same inputs
2. Capture new execution result
3. Compare with previous result
4. Determine verification status

**Verification Statuses**:
- `success` - Script now succeeds
- `same_error` - Same error persists
- `different_error` - New error appeared
- `timeout` - Script timed out

### 9. Script Runner (`core/runner.py`)

**Purpose**: Execute scripts and capture results.

**Features**:
- Subprocess execution with timeouts
- Working directory support
- Environment variable handling
- Output capture (stdout/stderr)
- Exit code tracking

### 10. Git Operations (`git/operations.py`, `git/pr.py`)

**Purpose**: Git and pull request management.

**Git Operations**:
- Branch creation and management
- Commit creation with templates
- Remote push operations
- Status checking

**PR Creation**:
- Pull request creation via gh CLI
- PR body formatting
- Draft PR support
- Auto-merge configuration

### 11. Notification System (`notifications/`)

**Purpose**: Multi-channel notification dispatch.

**Channels**:
- Slack (`slack.py`)
- Discord (`discord.py`)
- Email (`email.py`)
- GitHub Issues (`github_issues.py`)
- Custom Webhooks (`webhook.py`)

**Architecture**:
- `base.py` - Abstract base class
- `dispatcher.py` - Channel coordination
- Each channel implements `Notifier` protocol

### 12. Logging & History (`logging/`)

**Purpose**: Structured logging and session history.

**Components**:
- `logger.py` - Structured logging with Rich
- `formatters.py` - Log message formatting
- `history.py` - JSON-based history storage

**History Features**:
- Persistent JSON storage
- Queryable history (filter by script, limit)
- Record structure with all healing details

---

## Integration Points

### External Dependencies

1. **Claude Code CLI**
   - Interface: Subprocess with `-p` flag (prompt mode)
   - Communication: Command-line arguments and output parsing
   - Error handling: Exit codes and stderr capture

2. **GitHub CLI (gh)**
   - Interface: Subprocess for PR operations
   - Commands: `gh pr create`, `gh pr view`, etc.
   - Authentication: Uses gh's stored credentials

3. **Git**
   - Interface: Subprocess for git operations
   - Commands: `git log`, `git diff`, `git branch`, etc.
   - Repository: Works in current git repository

4. **Python Package Ecosystem**
   - Typer: CLI framework
   - Rich: Terminal output
   - Pydantic: Configuration validation
   - httpx: HTTP requests for webhooks
   - PyYAML: YAML parsing

---

## Module Responsibilities

```
lazarus/
├── __init__.py                # Package exports
├── __main__.py                # Entry point for python -m lazarus
├── cli.py                     # CLI commands and UI
│
├── config/                    # Configuration system
│   ├── __init__.py
│   ├── schema.py              # Pydantic models
│   └── loader.py              # Config loading and discovery
│
├── core/                      # Core healing logic
│   ├── __init__.py
│   ├── healer.py              # Main orchestrator
│   ├── context.py             # Context building
│   ├── runner.py              # Script execution
│   ├── verification.py        # Fix verification
│   ├── loop.py                # Retry loop management
│   └── truncation.py          # Output truncation
│
├── claude/                    # Claude Code integration
│   ├── __init__.py
│   ├── client.py              # CLI subprocess wrapper
│   ├── prompts.py             # Prompt building
│   └── parser.py              # Output parsing
│
├── security/                  # Security and redaction
│   ├── __init__.py
│   └── redactor.py            # Secrets redaction
│
├── git/                       # Git operations
│   ├── __init__.py
│   ├── operations.py          # Git commands
│   └── pr.py                  # Pull request creation
│
├── notifications/             # Notification channels
│   ├── __init__.py
│   ├── base.py                # Base classes
│   ├── dispatcher.py          # Channel coordination
│   ├── slack.py               # Slack integration
│   ├── discord.py             # Discord integration
│   ├── email.py               # Email sending
│   ├── github_issues.py       # GitHub Issues
│   └── webhook.py             # Custom webhooks
│
└── logging/                   # Logging and history
    ├── __init__.py
    ├── logger.py              # Structured logging
    ├── formatters.py          # Log formatting
    └── history.py             # Session history
```

---

## Design Principles

### 1. Simplicity Over Complexity

- Clear, linear execution flow
- Minimal abstractions
- Explicit is better than implicit
- Avoid premature optimization

### 2. CLI-First Approach

- Leverage existing tools (claude, gh, git)
- Subprocess calls over direct API integration
- Standard CLI patterns and conventions
- Works with standard Unix tools

### 3. Fail-Fast Validation

- Validate configuration at load time
- Check prerequisites before execution
- Clear error messages with actionable guidance
- Exit with meaningful status codes

### 4. Idempotent Operations

- Safe to re-run healing sessions
- No destructive operations without confirmation
- Git-based state management (no local database)
- Healing attempts are isolated

### 5. Type Safety

- Full type hints throughout codebase
- Mypy strict mode enabled
- Pydantic for runtime validation
- Clear contracts between modules

### 6. Security First

- Automatic secrets redaction
- No data storage beyond git/logs
- Minimal privilege requirements
- Clear security documentation

### 7. Beautiful Output

- Rich terminal formatting
- Progress indicators
- Color-coded status
- Structured tables and panels

### 8. Comprehensive Logging

- Structured logging format
- Debugging support with --verbose
- Persistent history
- Audit trail of all operations

---

## Extension Points

### Adding New Notification Channels

1. Implement `Notifier` protocol in `notifications/base.py`
2. Create new file in `notifications/`
3. Add configuration schema to `config/schema.py`
4. Register in `dispatcher.py`

Example:

```python
# notifications/teams.py
from lazarus.notifications.base import Notifier

class TeamsNotifier(Notifier):
    def notify(self, result: HealingResult) -> None:
        # Implementation
        pass
```

### Adding Custom Verification

1. Extend `VerificationResult` in `core/verification.py`
2. Add verification logic in `ScriptRunner.verify_fix()`
3. Update configuration schema if needed

### Adding New CLI Commands

1. Add `@app.command()` in `cli.py`
2. Implement command logic
3. Update help text and documentation

### Custom Healing Strategies

1. Extend `HealingLoop` in `core/loop.py`
2. Implement custom retry logic
3. Configure via `HealingConfig`

---

## Performance Considerations

### Timeouts

- Script execution timeout (configurable per script)
- Healing attempt timeout (configurable)
- Total healing timeout (failsafe)
- Subprocess timeouts for all external commands

### Resource Usage

- Subprocess isolation (no shared state)
- Output truncation for large logs (configured in `truncation.py`)
- Streaming subprocess output where possible
- Cleanup of temporary git branches

### Scalability

- Stateless design (scales horizontally)
- No centralized database requirement
- Works with standard CI/CD infrastructure
- Self-hosted runner support

---

## Testing Strategy

### Unit Tests

- Configuration validation
- Context building
- Redaction patterns
- Verification logic

### Integration Tests

- CLI command execution
- Git operations
- Notification sending

### End-to-End Tests

- Complete healing flow (marked with `@pytest.mark.e2e`)
- Actual Claude Code integration (skipped by default)
- PR creation workflow

---

## See Also

- [Getting Started](getting-started.md) - Installation and basic usage
- [Configuration](configuration.md) - Complete configuration reference
- [Security](security.md) - Security architecture and best practices
- [Troubleshooting](troubleshooting.md) - Common issues and debugging
