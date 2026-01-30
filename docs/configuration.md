# Configuration Reference

Complete reference for the `lazarus.yaml` configuration file.

## Table of Contents

- [Overview](#overview)
- [Configuration File Location](#configuration-file-location)
- [Root Schema](#root-schema)
- [Scripts Configuration](#scripts-configuration)
- [Healing Configuration](#healing-configuration)
- [Notifications Configuration](#notifications-configuration)
- [Git Configuration](#git-configuration)
- [Security Configuration](#security-configuration)
- [Logging Configuration](#logging-configuration)
- [Environment Variable Substitution](#environment-variable-substitution)
- [Example Configurations](#example-configurations)

---

## Overview

Lazarus uses a YAML configuration file (`lazarus.yaml`) to define scripts to monitor, healing behavior, notification preferences, and security settings. The configuration is validated using Pydantic v2 models with comprehensive validation rules.

### Configuration Precedence

1. Command-line flags (highest priority)
2. `lazarus.yaml` in current directory
3. `lazarus.yaml` in parent directories (up to repository root)
4. Default values (lowest priority)

### Validation

Validate your configuration before running:

```bash
lazarus validate
lazarus validate path/to/lazarus.yaml
```

---

## Configuration File Location

Lazarus searches for `lazarus.yaml` in the following order:

1. Path specified via `--config` flag
2. Current working directory
3. Parent directories (up to git repository root)

### Recommended Location

Place `lazarus.yaml` in your repository root alongside `.git/`:

```
my-project/
├── .git/
├── lazarus.yaml          # Configuration file
├── scripts/
│   ├── backup.py
│   └── deploy.sh
└── src/
```

---

## Root Schema

The root configuration object contains all Lazarus settings:

```yaml
scripts: []               # List of ScriptConfig objects
healing: {}               # HealingConfig object
notifications: {}         # NotificationConfig object
git: {}                   # GitConfig object
security: {}              # SecurityConfig object
logging: {}               # LoggingConfig object
```

All sections except `scripts` are optional and use sensible defaults.

---

## Scripts Configuration

Define scripts to monitor and heal. Each script has its own configuration.

### ScriptConfig Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Human-readable name for the script |
| `path` | path | Yes | - | Path to script file (relative to repo root) |
| `description` | string | No | null | Description of what the script does |
| `script_type` | string | No | auto-detected | Script type: `python`, `shell`, `node`, `other` |
| `schedule` | string | No | null | Cron expression for scheduled runs |
| `timeout` | int | No | per-type default | Execution timeout in seconds (1-86400) |
| `working_dir` | path | No | null | Working directory for script execution |
| `allowed_files` | list[str] | No | [] | Glob patterns for files Claude can modify |
| `forbidden_files` | list[str] | No | [] | Glob patterns for files Claude cannot modify |
| `environment` | list[str] | No | [] | Required environment variable names |
| `setup_commands` | list[str] | No | [] | Commands to run before script execution |
| `custom_prompt` | string | No | null | Additional context for Claude Code |
| `idempotent` | bool | No | true | Whether script is safe to re-run |
| `success_criteria` | dict | No | null | Custom success validation |

### Example

```yaml
scripts:
  - name: daily-backup
    path: scripts/backup.py
    description: Daily database backup to S3
    schedule: "0 2 * * *"  # 2 AM daily
    timeout: 600
    working_dir: /var/backups
    allowed_files:
      - "scripts/**/*.py"
      - "config/backup.yaml"
    forbidden_files:
      - "**/*.env"
      - "secrets/**"
    environment:
      - DATABASE_URL
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
    setup_commands:
      - "mkdir -p /var/backups/temp"
    custom_prompt: |
      This script backs up our production database.
      Be careful with S3 credentials and connection strings.
    idempotent: true
    success_criteria:
      exit_code: 0
      contains: "Backup completed successfully"
```

### Script Type and Default Timeouts

The `script_type` field determines the default timeout if not explicitly set:

| Script Type | Default Timeout | Auto-Detection |
|-------------|-----------------|----------------|
| `python` | 60 seconds | `.py` extension |
| `shell` | 180 seconds | `.sh`, `.bash` extensions |
| `node` | 90 seconds | `.js`, `.mjs`, `.ts` extensions |
| `other` | 120 seconds | All other extensions |

Shell scripts have longer default timeouts because they often run external commands that may take time. You can always override these defaults by explicitly setting the `timeout` field.

### Cron Schedule Format

The `schedule` field accepts standard cron expressions:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

Examples:
- `0 */6 * * *` - Every 6 hours
- `0 2 * * *` - Daily at 2 AM
- `0 0 * * 0` - Weekly on Sunday at midnight
- `*/15 * * * *` - Every 15 minutes

---

## Healing Configuration

Configure the AI-powered healing behavior.

### HealingConfig Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_attempts` | int | No | 3 | Maximum healing attempts (1-10) |
| `timeout_per_attempt` | int | No | 300 | Timeout per attempt in seconds (30-3600) |
| `total_timeout` | int | No | 900 | Total timeout for all attempts (60-7200) |
| `claude_model` | string | No | claude-sonnet-4-5-20250929 | Claude model to use |
| `max_turns` | int | No | 30 | Maximum conversation turns (1-100) |
| `allowed_tools` | list[str] | No | [] | Tools Claude can use (empty = all) |
| `forbidden_tools` | list[str] | No | [] | Tools Claude cannot use |

### Validation Rules

- `total_timeout` must be ≥ `timeout_per_attempt`
- If `total_timeout` < (`max_attempts` × `timeout_per_attempt`), some attempts may not run

### Example

```yaml
healing:
  max_attempts: 5
  timeout_per_attempt: 300
  total_timeout: 1500
  claude_model: claude-sonnet-4-5-20250929
  max_turns: 30
  allowed_tools:
    - Edit
    - Read
    - Write
  forbidden_tools:
    - Bash  # Prevent Claude from running arbitrary commands
```

### Available Claude Code Tools

- `Edit` - Modify existing files
- `Read` - Read file contents
- `Write` - Create new files
- `Bash` - Execute bash commands
- `Glob` - Search for files by pattern
- `Grep` - Search file contents

**Security Note**: Restricting `allowed_tools` to `[Edit, Read, Write]` is recommended for production use.

---

## Notifications Configuration

Configure notifications for healing results.

### NotificationConfig Schema

```yaml
notifications:
  slack: {}           # SlackConfig
  discord: {}         # DiscordConfig
  email: {}           # EmailConfig
  github_issues: {}   # GitHubIssuesConfig
  webhook: {}         # WebhookConfig
```

All notification channels are optional. Multiple channels can be configured simultaneously.

### Slack Notifications

```yaml
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#alerts"  # Optional channel override
    on_success: true
    on_failure: true
```

### Discord Notifications

```yaml
notifications:
  discord:
    webhook_url: "${DISCORD_WEBHOOK_URL}"
    on_success: true
    on_failure: true
```

### Email Notifications

```yaml
notifications:
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from_addr: lazarus@example.com
    to_addrs:
      - team@example.com
      - oncall@example.com
    on_success: false
    on_failure: true
    use_tls: true
```

### GitHub Issues

```yaml
notifications:
  github_issues:
    repo: owner/repository
    labels:
      - lazarus
      - auto-heal
      - bug
    on_failure: true
    assignees:
      - devops-team
```

### Custom Webhook

```yaml
notifications:
  webhook:
    url: "${CUSTOM_WEBHOOK_URL}"
    method: POST
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
      Content-Type: application/json
    on_success: true
    on_failure: true
```

---

## Git Configuration

Configure pull request creation and git behavior.

### GitConfig Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `create_pr` | bool | No | true | Create pull requests automatically |
| `branch_prefix` | string | No | lazarus/fix | Prefix for healing branches |
| `draft_pr` | bool | No | false | Create PRs as drafts |
| `auto_merge` | bool | No | false | Enable auto-merge if checks pass |
| `commit_message_template` | string | No | null | Template for commit messages |
| `pr_title_template` | string | No | null | Template for PR titles |
| `pr_body_template` | string | No | null | Template for PR bodies |

### Example

```yaml
git:
  create_pr: true
  branch_prefix: "lazarus/heal"
  draft_pr: true  # Create as draft for manual review
  auto_merge: false
  commit_message_template: |
    Fix: {script_name}

    {explanation}

    Healed by Lazarus
  pr_title_template: "Fix: {script_name} - {summary}"
  pr_body_template: |
    ## Automated Fix

    {explanation}

    ### Changes
    {files_changed}

    ### Verification
    Script executed successfully after fix.
```

### Template Variables

Available variables for templates:
- `{script_name}` - Name of the script
- `{script_path}` - Path to the script
- `{explanation}` - Claude's explanation of the fix
- `{files_changed}` - List of modified files
- `{summary}` - Short summary of the fix
- `{timestamp}` - ISO timestamp of healing

---

## Security Configuration

Configure secrets redaction and security patterns.

### SecurityConfig Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `redact_patterns` | list[str] | No | Built-in patterns | Regex patterns for secret detection |
| `additional_patterns` | list[str] | No | [] | User-defined regex patterns |
| `safe_env_vars` | list[str] | No | Safe defaults | Environment variables safe to expose |

### Built-in Redaction Patterns

Lazarus automatically redacts:
- API keys and tokens
- Passwords and secrets
- AWS credentials
- Private keys
- Bearer tokens
- Authorization headers

### Example

```yaml
security:
  additional_patterns:
    - "(?i)(database[_-]?password)[\s=:]+['\"]?([^\s'\"]{8,})['\"]?"
    - "(?i)(stripe[_-]?key)[\s=:]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?"
  safe_env_vars:
    - PATH
    - HOME
    - USER
    - SHELL
    - LANG
    - TERM
    - NODE_ENV
    - ENVIRONMENT
```

### Pattern Format

Patterns use Python regex syntax. Capture groups are replaced with `[REDACTED:pattern_name]`.

---

## Logging Configuration

Configure logging behavior and output.

### LoggingConfig Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `level` | string | No | INFO | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `format` | string | No | Standard format | Python log format string |
| `file` | path | No | null | Log file path |
| `rotation` | int | No | 10 | Log rotation size in MB (0 = no rotation) |
| `retention` | int | No | 10 | Number of rotated logs to keep (1-100) |
| `console` | bool | No | true | Log to console |

### Example

```yaml
logging:
  level: DEBUG
  console: true
  file: logs/lazarus.log
  rotation: 50  # 50 MB per file
  retention: 20  # Keep 20 old logs
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## Environment Variable Substitution

Lazarus supports environment variable substitution in configuration values using `${VAR_NAME}` syntax.

### Supported Fields

Environment variables can be used in:
- Notification webhook URLs
- Email credentials
- Custom headers
- Any string field in the configuration

### Example

```yaml
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"

  email:
    username: "${SMTP_USER}"
    password: "${SMTP_PASS}"

  webhook:
    url: "${CUSTOM_WEBHOOK}"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

### Environment File

Store sensitive values in a `.env` file (never commit this):

```bash
# .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SMTP_USER=notifications@example.com
SMTP_PASS=your-password-here
API_TOKEN=your-api-token
```

Load it before running Lazarus:

```bash
export $(cat .env | xargs)
lazarus run scripts/backup.py
```

---

## Example Configurations

### Minimal Configuration

```yaml
scripts:
  - name: my-script
    path: scripts/example.py

healing:
  max_attempts: 3

git:
  create_pr: true
```

### Production Configuration

```yaml
scripts:
  - name: critical-backup
    path: scripts/backup.py
    description: Critical database backup
    timeout: 600
    allowed_files:
      - "scripts/**/*.py"
    forbidden_files:
      - "**/*.env"
      - "secrets/**"
    environment:
      - DATABASE_URL
      - AWS_ACCESS_KEY_ID

healing:
  max_attempts: 5
  timeout_per_attempt: 300
  total_timeout: 1800
  claude_model: claude-sonnet-4-5-20250929
  allowed_tools:
    - Edit
    - Read
    - Write

notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_success: false
    on_failure: true

  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: "${SMTP_USER}"
    password: "${SMTP_PASS}"
    from_addr: lazarus@company.com
    to_addrs:
      - oncall@company.com
    on_success: false
    on_failure: true

  github_issues:
    repo: company/infrastructure
    labels:
      - lazarus
      - critical
      - auto-heal
    on_failure: true

git:
  create_pr: true
  branch_prefix: "lazarus/critical-fix"
  draft_pr: false
  auto_merge: false

security:
  additional_patterns:
    - "(?i)(db[_-]?password)[\s=:]+['\"]?([^\s'\"]{8,})['\"]?"
  safe_env_vars:
    - PATH
    - HOME
    - USER
    - ENVIRONMENT

logging:
  level: INFO
  console: true
  file: /var/log/lazarus/healing.log
  rotation: 50
  retention: 30
```

### CI/CD Configuration

```yaml
scripts:
  - name: deployment
    path: scripts/deploy.sh
    timeout: 1800
    working_dir: /app
    allowed_files:
      - "scripts/**"
      - "config/**"
      - "deploy/**"
    forbidden_files:
      - ".env*"
      - "secrets/**"
      - "*.pem"

healing:
  max_attempts: 2
  timeout_per_attempt: 600
  total_timeout: 1200
  allowed_tools:
    - Edit
    - Read

git:
  create_pr: true
  branch_prefix: "lazarus/deploy-fix"
  draft_pr: true  # Always review deployment fixes

notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#deployments"
    on_success: true
    on_failure: true

logging:
  level: INFO
  console: true
```

---

## Validation Rules

### Script Validation

- Script names must be unique
- Script paths must exist (when running heal/run commands)
- Cron schedules must have 5 or 6 fields
- Timeout must be between 1 and 86400 seconds

### Healing Validation

- `max_attempts` must be between 1 and 10
- `timeout_per_attempt` must be between 30 and 3600 seconds
- `total_timeout` must be between 60 and 7200 seconds
- `total_timeout` ≥ `timeout_per_attempt`

### Security Validation

- All redaction patterns must be valid regex
- Pattern compilation is checked at config load time

### Notification Validation

- Webhook URLs must be valid HTTP/HTTPS URLs
- Email addresses must be valid format
- GitHub repo must match `owner/repo` pattern
- SMTP port must be between 1 and 65535

---

## See Also

- [Getting Started](getting-started.md) - Installation and first run
- [Examples](examples.md) - Real-world configuration examples
- [Security](security.md) - Security best practices
- [CLI Reference](cli-reference.md) - Command-line interface documentation
