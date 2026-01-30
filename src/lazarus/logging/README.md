# Lazarus Logging & History System

This module provides structured logging and healing history tracking for the Lazarus self-healing system.

## Components

### 1. LazarusLogger (`logger.py`)

Structured JSON logger that records all healing events with rich console output and JSON file output.

**Features:**
- JSON-formatted file logging for machine parsing
- Rich console output with colors and formatting
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation based on size (configurable MB threshold)
- Specialized methods for healing events

**Usage:**

```python
from lazarus.config.schema import LoggingConfig
from lazarus.logging import LazarusLogger

# Initialize logger
config = LoggingConfig(
    level="INFO",
    console=True,
    file="logs/lazarus.log",
    rotation=10,  # 10 MB per file
    retention=10,  # Keep 10 backup files
)
logger = LazarusLogger(config)

# Log healing events
logger.log_healing_start(
    script_path=Path("scripts/backup.py"),
    max_attempts=3,
    timeout=300,
)

logger.log_healing_attempt(
    script_path=Path("scripts/backup.py"),
    attempt_number=1,
    max_attempts=3,
)

logger.log_healing_complete(
    script_path=Path("scripts/backup.py"),
    result=healing_result,
)

# General logging
logger.info("Script execution started")
logger.error("Failed to connect to database", exc_info=True)
```

**Log Format:**

File logs are in JSON format:
```json
{
  "timestamp": "2025-01-30T12:34:56.789Z",
  "level": "INFO",
  "logger": "lazarus",
  "message": "Starting healing session for backup.py",
  "event_type": "healing_start",
  "script_path": "/path/to/scripts/backup.py",
  "details": {
    "max_attempts": 3,
    "timeout": 300
  }
}
```

### 2. HealingHistory (`history.py`)

Tracks and persists healing session results to disk, allowing query and analysis of past healing attempts.

**Features:**
- Persistent storage as JSON files
- Query history with filtering and pagination
- Calculate success rates
- Cleanup old records
- Unique record IDs for tracking

**Usage:**

```python
from lazarus.logging import HealingHistory

# Initialize history tracker
history = HealingHistory(history_dir=Path(".lazarus-history"))

# Record a healing session
record_id = history.record(
    result=healing_result,
    script_path=Path("scripts/backup.py"),
)

# Get recent history
recent = history.get_history(limit=10)
for record in recent:
    print(f"{record.timestamp}: {record.script_path} - Success: {record.success}")

# Filter by script
backup_history = history.get_history(
    limit=20,
    script_filter="backup",
)

# Get specific record
record = history.get_record(record_id)
if record:
    print(f"Success: {record.success}")
    print(f"Attempts: {record.attempts_count}")
    print(f"Duration: {record.duration}s")

# Calculate success rate
success_rate = history.get_success_rate()
print(f"Overall success rate: {success_rate * 100:.1f}%")

# Cleanup old records (older than 30 days)
removed = history.cleanup_old_records(days=30)
print(f"Removed {removed} old records")
```

**HistoryRecord Structure:**

```python
@dataclass
class HistoryRecord:
    id: str                      # Unique UUID
    timestamp: str               # ISO 8601 timestamp
    script_path: str             # Full path to script
    success: bool                # Healing success status
    attempts_count: int          # Number of attempts made
    duration: float              # Total duration in seconds
    pr_url: Optional[str]        # PR URL if created
    error_summary: Optional[str] # Error message if failed
```

### 3. Formatters (`formatters.py`)

Utilities for formatting healing results for display in the CLI.

**Features:**
- Human-readable summary formatting
- JSON output for programmatic use
- Rich table display

**Usage:**

```python
from lazarus.logging import format_healing_summary, format_healing_json, display_healing_result_table
from rich.console import Console

# Format as text summary
summary = format_healing_summary(result)
print(summary)

# Format as JSON
json_output = format_healing_json(result)
with open("result.json", "w") as f:
    f.write(json_output)

# Display as rich table
console = Console()
display_healing_result_table(result, console=console)
```

## CLI Integration

The logging and history system is integrated into the CLI:

### History Command

```bash
# View recent healing history
lazarus history

# Show more records
lazarus history --limit 20

# Filter by script name
lazarus history --script backup.py

# Output as JSON
lazarus history --json > history.json
```

### Heal Command

The `heal` command automatically:
1. Initializes the logger with configuration from `lazarus.yaml`
2. Logs healing start, attempts, and completion
3. Records the session in history
4. Displays results with rich formatting

## Configuration

Configure logging in `lazarus.yaml`:

```yaml
logging:
  level: INFO                    # DEBUG, INFO, WARNING, ERROR
  console: true                  # Log to console
  file: logs/lazarus.log        # Log file path (optional)
  rotation: 10                   # Rotation size in MB (0 = no rotation)
  retention: 10                  # Number of backup files to keep
```

## Log Rotation

When rotation is enabled (rotation > 0):
- Log files are rotated when they reach the specified size
- Backup files are named: `lazarus.log.1`, `lazarus.log.2`, etc.
- Oldest backups are deleted when retention limit is reached
- Uses Python's `RotatingFileHandler`

## History Storage

History records are stored in `.lazarus-history/` by default:
- Each record is a JSON file named `{uuid}.json`
- Files are sorted by timestamp for efficient querying
- Records can be cleaned up with `cleanup_old_records()`

## Event Types

The logger tracks these event types:
- `healing_start` - Healing session begins
- `healing_attempt` - Individual healing attempt
- `healing_complete` - Healing session ends (success or failure)
- `error` - General error occurred

## Best Practices

1. Always use the LazarusLogger for healing-related events
2. Record all healing sessions in history for analysis
3. Configure appropriate log rotation to prevent disk space issues
4. Regularly cleanup old history records
5. Use JSON output for programmatic analysis
6. Filter history by script for targeted debugging

## Testing

Unit tests are provided in `tests/unit/`:
- `test_logger.py` - Tests for LazarusLogger and JSONFormatter
- `test_history.py` - Tests for HealingHistory and HistoryRecord

Run tests:
```bash
pytest tests/unit/test_logger.py -v
pytest tests/unit/test_history.py -v
```

## Examples

See the CLI implementation in `src/lazarus/cli.py` for integration examples.
