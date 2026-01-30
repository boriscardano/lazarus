# Healing Loop Orchestration

This document describes the healing loop orchestration system in Lazarus, which is the core component that coordinates the self-healing process.

## Overview

The healing loop orchestration consists of three main components:

1. **Healer** (`src/lazarus/core/healer.py`) - Main orchestrator
2. **HealingLoop** (`src/lazarus/core/loop.py`) - Retry loop manager
3. **CLI** (`src/lazarus/cli.py`) - Command-line interface

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI (Typer)                          │
│  Commands: heal, run, history, validate, init, check   │
└────────────────────┬────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────┐
│                    Healer                               │
│  - Orchestrates healing process                         │
│  - Manages Claude Code client                           │
│  - Tracks attempts and results                          │
└────────┬───────────────────────────┬────────────────────┘
         │                           │
         v                           v
┌────────────────────┐    ┌─────────────────────────────┐
│   HealingLoop      │    │   ScriptRunner              │
│  - Retry logic     │    │  - Execute scripts          │
│  - Timeout mgmt    │    │  - Verify fixes             │
│  - Attempt count   │    │  - Compare results          │
└────────────────────┘    └─────────────────────────────┘
```

## Components

### 1. Healer

The `Healer` class is the heart of Lazarus. It orchestrates the entire healing process:

```python
from lazarus.core.healer import Healer
from lazarus.config.loader import load_config

# Load configuration
config = load_config()

# Create healer
healer = Healer(config)

# Heal a script
result = healer.heal(Path("scripts/failing_script.py"))

if result.success:
    print(f"Healed in {len(result.attempts)} attempts!")
else:
    print(f"Failed: {result.error_message}")
```

#### Healing Process Flow

1. **Validate Script**: Check that the script exists and is executable
2. **Initial Run**: Execute the script to capture the failure
3. **Check Success**: If script succeeds, return early (no healing needed)
4. **Build Context**: Create comprehensive context with error, git state, system info
5. **Healing Loop**: For each attempt (up to max_attempts):
   - Request fix from Claude Code
   - Verify the fix by re-running the script
   - Check status:
     - `success`: Break and return success
     - `same_error`: Continue with enhanced context
     - `different_error`: Update context with new error
     - `timeout`: Continue with timeout information
6. **Return Result**: Package all attempts and final status

#### Key Methods

- `heal(script_path: Path) -> HealingResult`: Main healing method
- `_run_script(script_path, config)`: Run script with configuration
- `_find_script_config(script_path)`: Find matching script config
- `_has_uncommitted_changes(script_path)`: Check for uncommitted changes
- `_enhance_context_for_retry(context, attempt, number)`: Enhance context for retry

### 2. HealingLoop

The `HealingLoop` class manages the retry logic with timing enforcement:

```python
from lazarus.core.loop import HealingLoop

# Create loop
loop = HealingLoop(
    max_attempts=3,
    timeout_per_attempt=300,
    total_timeout=900,
)

# Iterate through attempts
for attempt_number in loop:
    # Perform healing attempt
    success = perform_healing()

    if success:
        loop.mark_success()
        break

    # Loop automatically handles max attempts and timeouts
```

#### Key Features

- **Attempt Counting**: Tracks current attempt (1-indexed)
- **Timeout Enforcement**:
  - Per-attempt timeout
  - Total timeout across all attempts
- **Early Exit**: `mark_success()` to exit on success
- **Time Tracking**:
  - `get_elapsed_time()`: Time since loop started
  - `get_remaining_time()`: Time until total timeout
  - `get_attempts_remaining()`: Attempts left

#### Iterator Interface

The loop provides an iterator interface:

```python
for attempt_num in loop:
    # attempt_num is 1-indexed
    print(f"Attempt {attempt_num}")

    # Check remaining resources
    if loop.get_remaining_time() < 60:
        print("Less than 60s remaining!")
```

### 3. CLI

The CLI provides a user-friendly interface using Typer and Rich:

```bash
# Heal a specific script
lazarus heal scripts/backup.py

# Run and heal if needed
lazarus run scripts/deploy.sh

# View history
lazarus history --limit 20

# Validate configuration
lazarus validate

# Create configuration template
lazarus init --full

# Check prerequisites
lazarus check
```

#### Commands

##### heal
Heal a specific script that is failing.

```bash
lazarus heal SCRIPT_PATH [OPTIONS]

Options:
  --max-attempts, -n INTEGER    Maximum healing attempts
  --timeout, -t INTEGER         Total timeout in seconds
  --no-pr                       Skip PR creation
  --dry-run                     Check only, no changes
  --verbose, -v                 Show detailed output
  --config, -c PATH             Path to lazarus.yaml
```

##### run
Run a script and heal it if it fails.

```bash
lazarus run SCRIPT_PATH [OPTIONS]
```

Same options as `heal`.

##### history
View healing history.

```bash
lazarus history [OPTIONS]

Options:
  --limit, -n INTEGER          Number of sessions to show
  --script, -s TEXT            Filter by script name
  --json                       Output as JSON
```

##### validate
Validate lazarus.yaml configuration.

```bash
lazarus validate [CONFIG_PATH] [OPTIONS]

Options:
  --verbose, -v                Show detailed output
```

##### init
Create a lazarus.yaml template.

```bash
lazarus init [OPTIONS]

Options:
  --full                       Create full template
  --output, -o PATH            Output path
  --force, -f                  Overwrite existing file
```

##### check
Check prerequisites (claude, gh, git).

```bash
lazarus check [OPTIONS]

Options:
  --verbose, -v                Show detailed output
```

## Data Structures

### HealingResult

Complete result of the healing process:

```python
@dataclass
class HealingResult:
    success: bool                      # Overall success
    attempts: list[HealingAttempt]     # All attempts made
    final_execution: ExecutionResult   # Final run result
    pr_url: str | None                 # PR URL if created
    duration: float                    # Total duration (seconds)
    error_message: str | None          # Error if failed
```

### HealingAttempt

Record of a single healing attempt:

```python
@dataclass
class HealingAttempt:
    attempt_number: int               # Attempt number (1-indexed)
    claude_response: ClaudeResponse   # Claude's response
    verification: VerificationResult  # Verification result
    duration: float                   # Attempt duration (seconds)
```

## Configuration

Healing behavior is controlled by the `healing` section in `lazarus.yaml`:

```yaml
healing:
  max_attempts: 3              # Maximum healing attempts
  timeout_per_attempt: 300     # Max time per attempt (seconds)
  total_timeout: 900           # Max total time (seconds)
  claude_model: claude-sonnet-4-5-20250929
  max_turns: 30                # Max conversation turns
  allowed_tools: []            # Specific tools (empty = all)
  forbidden_tools: []          # Tools to forbid
```

## Error Handling

### Script Not Found
```python
try:
    result = healer.heal(Path("nonexistent.py"))
except FileNotFoundError as e:
    print(f"Script not found: {e}")
```

### Configuration Errors
```python
from lazarus.config.loader import ConfigError

try:
    config = load_config()
except ConfigError as e:
    print(f"Config error: {e}")
```

### Timeout Handling
Timeouts are handled gracefully:
- Per-attempt timeout: Script execution is terminated
- Total timeout: Loop exits early
- Results include partial information

## Best Practices

### 1. Script Requirements
- Scripts should be idempotent (safe to re-run)
- Clear error messages improve healing success
- Scripts should have reasonable timeouts

### 2. Configuration
- Set `max_attempts` based on script complexity
- Use `total_timeout` to prevent runaway healing
- Configure `allowed_files` to limit scope

### 3. Monitoring
- Review healing history regularly
- Monitor success rates
- Adjust timeouts based on patterns

### 4. Security
- Use `forbidden_files` for sensitive files
- Review Claude's changes before merging PRs
- Enable notifications for healing events

## Examples

### Basic Healing
```python
from lazarus.core.healer import Healer
from lazarus.config.loader import load_config

config = load_config()
healer = Healer(config)

result = healer.heal(Path("scripts/backup.py"))
print(f"Success: {result.success}")
print(f"Attempts: {len(result.attempts)}")
print(f"Duration: {result.duration:.2f}s")
```

### Custom Configuration
```python
from lazarus.config.schema import HealingConfig, LazarusConfig

config = LazarusConfig(
    healing=HealingConfig(
        max_attempts=5,
        timeout_per_attempt=600,
        total_timeout=3000,
    )
)

healer = Healer(config)
result = healer.heal(Path("complex_script.py"))
```

### Verbose Output
```python
result = healer.heal(script_path)

for attempt in result.attempts:
    print(f"\nAttempt {attempt.attempt_number}:")
    print(f"  Claude: {attempt.claude_response.explanation}")
    print(f"  Status: {attempt.verification.status}")
    print(f"  Files: {attempt.claude_response.files_changed}")
```

## Testing

### Unit Tests
```bash
# Run healer tests
pytest tests/unit/test_healer.py -v

# Run loop tests
pytest tests/unit/test_loop.py -v

# Run CLI tests
pytest tests/unit/test_cli.py -v
```

### Integration Tests
```bash
# Test end-to-end healing
pytest tests/integration/test_healing_e2e.py -v
```

## Troubleshooting

### Claude Code Not Available
```
Error: Claude Code CLI is not available
Solution: npm install -g @anthropic-ai/claude-code
```

### Timeout Issues
```
Error: Script execution exceeded timeout
Solution: Increase timeout_per_attempt or total_timeout
```

### Same Error Repeating
```
Status: same_error across all attempts
Solution:
- Check if error is fixable automatically
- Review custom_prompt configuration
- Verify allowed_files includes necessary files
```

### Different Error Each Attempt
```
Status: different_error on each attempt
Solution:
- Script may have non-deterministic behavior
- Check if script is idempotent
- Review script dependencies
```

## Performance Considerations

### Optimization Tips
1. **Set Reasonable Timeouts**: Avoid unnecessarily long timeouts
2. **Limit Attempts**: 3-5 attempts is usually sufficient
3. **Use Script Configs**: Pre-configure common scripts
4. **Enable Caching**: (Future feature)

### Resource Usage
- Memory: ~50-100MB per healing session
- CPU: Depends on script complexity
- Network: Claude API calls (~1-2 per attempt)

## Future Enhancements

- [ ] Parallel healing for multiple scripts
- [ ] Learning from previous healing sessions
- [ ] Healing analytics and insights
- [ ] Custom healing strategies
- [ ] Webhook notifications during healing
- [ ] Resume interrupted healing sessions
