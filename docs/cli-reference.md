# CLI Reference

Complete reference for the Lazarus command-line interface.

## Installation

```bash
# Install from PyPI (when published)
uv pip install lazarus-heal

# Or install from source (recommended: use uv)
git clone https://github.com/boriscardano/lazarus.git
cd lazarus
uv pip install -e .

# Or with pip
pip install -e .
```

## Quick Start

```bash
# Initialize configuration
lazarus init

# Edit lazarus.yaml to configure your scripts

# Validate configuration
lazarus validate

# Check prerequisites
lazarus check

# Heal a failing script
lazarus heal scripts/backup.py
```

## Commands

### heal

Heal a specific script that is failing.

**Usage:**
```bash
lazarus heal SCRIPT_PATH [OPTIONS]
```

**Arguments:**
- `SCRIPT_PATH`: Path to the script to heal (required)

**Options:**
- `--max-attempts, -n INTEGER`: Maximum healing attempts (overrides config)
  - Min: 1, Max: 10
  - Default: From config (usually 3)
- `--timeout, -t INTEGER`: Total timeout in seconds (overrides config)
  - Min: 60
  - Default: From config (usually 900)
- `--no-pr`: Skip PR creation even if enabled in config
- `--dry-run`: Run without making changes (check only)
- `--verbose, -v`: Show detailed output
- `--config, -c PATH`: Path to lazarus.yaml (auto-detected if not provided)

**Examples:**
```bash
# Basic healing
lazarus heal scripts/backup.py

# With more attempts
lazarus heal scripts/complex.py --max-attempts 5

# Verbose output
lazarus heal scripts/deploy.sh --verbose

# Dry run (no changes)
lazarus heal scripts/test.py --dry-run

# Custom config location
lazarus heal scripts/sync.py --config config/lazarus.yaml
```

**Exit Codes:**
- `0`: Success (script healed or already working)
- `1`: Healing failed
- `2`: Configuration or file error
- `3`: Unexpected error

---

### run

Run a script and heal it if it fails.

**Usage:**
```bash
lazarus run SCRIPT_PATH [OPTIONS]
```

**Arguments:**
- `SCRIPT_PATH`: Path to the script to run (required)

**Options:**
Same as `heal` command (except `--dry-run`)

**Examples:**
```bash
# Run script, heal if it fails
lazarus run scripts/daily-job.py

# With custom timeout
lazarus run scripts/long-task.sh --timeout 1800

# Skip PR creation
lazarus run scripts/quick-fix.py --no-pr
```

**Notes:**
- If the script succeeds on first run, no healing is performed
- This is essentially an alias for `heal` with friendlier naming

---

### history

View healing history.

**Usage:**
```bash
lazarus history [OPTIONS]
```

**Options:**
- `--limit, -n INTEGER`: Number of recent healing sessions to show
  - Min: 1, Max: 100
  - Default: 10
- `--script, -s TEXT`: Filter by script name or path
- `--json`: Output as JSON format

**Examples:**
```bash
# View last 10 healing sessions
lazarus history

# View last 20 sessions
lazarus history --limit 20

# Filter by script
lazarus history --script backup.py

# JSON output for processing
lazarus history --json > history.json
```

**Note:** History feature will be available in a future release.

---

### validate

Validate lazarus.yaml configuration file.

**Usage:**
```bash
lazarus validate [CONFIG_PATH] [OPTIONS]
```

**Arguments:**
- `CONFIG_PATH`: Path to lazarus.yaml (optional, auto-detected if not provided)

**Options:**
- `--verbose, -v`: Show detailed validation output

**Examples:**
```bash
# Validate auto-detected config
lazarus validate

# Validate specific config file
lazarus validate config/lazarus.yaml

# Verbose output
lazarus validate --verbose
```

**Exit Codes:**
- `0`: Configuration is valid
- `1`: Validation failed
- `2`: Error reading or parsing file

**Validation Checks:**
- YAML syntax
- Required fields
- Field types
- Value constraints (min/max)
- Cross-field validation
- Regex patterns
- Environment variable expansion

---

### init

Create a lazarus.yaml configuration template.

**Usage:**
```bash
lazarus init [OPTIONS]
```

**Options:**
- `--full`: Create full configuration template with all options
  - Default: Create minimal template
- `--output, -o PATH`: Output path
  - Default: `./lazarus.yaml`
- `--force, -f`: Overwrite existing configuration file

**Examples:**
```bash
# Create minimal template
lazarus init

# Create full template with all options
lazarus init --full

# Custom output location
lazarus init --output config/lazarus.yaml

# Overwrite existing file
lazarus init --force
```

**Templates:**

*Minimal Template:*
- Basic script configuration
- Essential healing settings
- Git PR creation
- Console logging

*Full Template:*
- All configuration options
- Multiple script examples
- Notification configurations
- Advanced security settings
- Comprehensive logging options

---

### diagnose

Diagnose a script without making changes (read-only analysis).

**Usage:**
```bash
lazarus diagnose SCRIPT_PATH [OPTIONS]
```

**Arguments:**
- `SCRIPT_PATH`: Path to the script to diagnose (required)

**Options:**
- `--timeout, -t INTEGER`: Timeout in seconds for analysis
  - Min: 60
  - Default: 300
- `--verbose, -v`: Show detailed output
- `--config, -c PATH`: Path to lazarus.yaml (auto-detected if not provided)

**Examples:**
```bash
# Diagnose a failing script
lazarus diagnose scripts/backup.py

# With verbose output
lazarus diagnose scripts/complex.py --verbose

# Custom timeout
lazarus diagnose scripts/slow.py --timeout 600
```

**Notes:**
- This is a read-only operation - no files are modified
- Claude Code is restricted to using only the Read tool
- Useful for understanding issues before deciding to heal
- Returns diagnosis with suggested fixes but does not apply them

**Exit Codes:**
- `0`: Analysis completed successfully
- `1`: Analysis failed
- `2`: Configuration or file error

---

### check

Check prerequisites (claude, gh, git).

**Usage:**
```bash
lazarus check [OPTIONS]
```

**Options:**
- `--verbose, -v`: Show detailed check output

**Examples:**
```bash
# Basic check
lazarus check

# Verbose output with versions
lazarus check --verbose
```

**Checks:**
1. **git**: Git version control
   - Required: Yes
   - Install: https://git-scm.com/downloads
2. **gh**: GitHub CLI
   - Required: For PR creation
   - Install: https://cli.github.com/
3. **claude**: Claude Code CLI
   - Required: Yes
   - Install: `npm install -g @anthropic-ai/claude-code`

**Exit Codes:**
- `0`: All prerequisites available
- `1`: One or more prerequisites missing

---

## Global Options

None currently. All options are command-specific.

## Environment Variables

### CLAUDE_API_KEY
Claude API key for authentication (if using API directly).

**Example:**
```bash
export CLAUDE_API_KEY=sk-ant-...
```

### Configuration Variables
Any variable in `${VAR}` format in lazarus.yaml can be set:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export DATABASE_URL=postgresql://...
```

## Output Formats

### Standard Output
Rich formatted output with:
- Colored text
- Progress indicators
- Tables
- Panels with borders
- Status icons (✓, ✗)

### JSON Output
Available for `history` command:

```json
{
  "sessions": [
    {
      "id": "session-123",
      "script": "scripts/backup.py",
      "success": true,
      "attempts": 2,
      "duration": 45.2,
      "timestamp": "2024-01-30T10:30:00Z"
    }
  ]
}
```

## Configuration File

See [Configuration Guide](configuration.md) for detailed information.

**Location:**
- Auto-detected from current directory or parents
- Custom location with `--config` option

**Format:**
```yaml
scripts:
  - name: script-name
    path: scripts/script.py
    # ... more options

healing:
  max_attempts: 3
  # ... more options

# ... other sections
```

## Exit Codes

Consistent exit codes across all commands:

- `0`: Success
- `1`: Operation failed (e.g., healing failed, validation failed)
- `2`: Configuration or file error
- `3`: Unexpected error

## Shell Completion

**Bash:**
```bash
lazarus --install-completion bash
```

**Zsh:**
```bash
lazarus --install-completion zsh
```

**Fish:**
```bash
lazarus --install-completion fish
```

## Logging

Logs are written to:
- Console (if enabled in config)
- Log file (if specified in config)

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

**Configuration:**
```yaml
logging:
  level: INFO
  console: true
  file: logs/lazarus.log
  rotation: 10  # MB
  retention: 10  # number of files
```

## Tips and Tricks

### Dry Run Before Healing
```bash
# Check what would happen without making changes
lazarus heal scripts/important.py --dry-run
```

### Increase Verbosity for Debugging
```bash
# See detailed output
lazarus heal scripts/failing.py --verbose
```

### Validate Before Running
```bash
# Always validate config after changes
lazarus validate && lazarus heal scripts/backup.py
```

### Check Prerequisites First
```bash
# Ensure all tools are installed
lazarus check && lazarus heal scripts/deploy.sh
```

### Use Custom Timeouts for Long Scripts
```bash
# Increase timeout for long-running scripts
lazarus heal scripts/long-task.py --timeout 3600
```

## Troubleshooting

### Command Not Found
```bash
# Error: lazarus: command not found
# Solution: Ensure pip install location is in PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Permission Denied
```bash
# Error: Permission denied: scripts/backup.py
# Solution: Make script executable
chmod +x scripts/backup.py
```

### Config Not Found
```bash
# Error: Configuration file not found
# Solution: Initialize config or specify path
lazarus init
# OR
lazarus heal script.py --config /path/to/lazarus.yaml
```

### Claude Not Authenticated
```bash
# Error: Claude Code authentication failed
# Solution: Login to Claude
claude login
```

## Examples

### Daily Backup Script
```bash
# Configure
cat > lazarus.yaml <<EOF
scripts:
  - name: daily-backup
    path: scripts/backup.sh
    timeout: 600
healing:
  max_attempts: 3
EOF

# Validate
lazarus validate

# Run (creates cron job)
crontab -e
# Add: 0 2 * * * cd /path/to/repo && lazarus run scripts/backup.sh
```

### CI/CD Integration
```yaml
# .github/workflows/scheduled-tasks.yml
name: Scheduled Tasks
on:
  schedule:
    - cron: '0 */6 * * *'
jobs:
  run-tasks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install lazarus-heal
      - run: lazarus run scripts/sync-data.py
```

### Multi-Script Healing
```bash
# Heal multiple scripts
for script in scripts/*.py; do
  lazarus heal "$script" || echo "Failed: $script"
done
```

## See Also

- [Configuration Guide](configuration.md)
- [Healing Loop Documentation](healing-loop.md)
- [API Reference](api-reference.md)
- [Examples](../examples/)
