# Lazarus

**Self-healing script runner powered by Claude Code**

Lazarus automatically detects failing scripts, uses AI to diagnose and fix issues, creates pull requests with the fixes, and notifies you of the results. It's designed to run as part of your CI/CD pipeline or as a scheduled maintenance tool.

## Features

- **Automatic Healing**: Detects script failures and uses Claude Code to analyze and fix issues
- **Smart Context Building**: Collects stdout/stderr, exit codes, script content, git history, and system info
- **Security-First**: Automatic secrets redaction before sending to AI
- **PR Automation**: Creates well-structured pull requests with fix descriptions
- **Multi-Channel Notifications**: Slack, Discord, Email, GitHub Issues, or custom webhooks
- **Flexible Execution**: Run on-demand, on failure, or on a schedule via GitHub Actions
- **Self-Hosted Runner Support**: Full guides for macOS (launchd) and Linux (systemd)

## Quick Start

### Installation

```bash
# Using pip
pip install lazarus-heal

# Or install from source using our installation script
git clone https://github.com/yourusername/lazarus.git
cd lazarus
./scripts/install.sh

# For development
./scripts/install.sh --dev
```

See [scripts/README.md](scripts/README.md) for detailed installation options.

### Prerequisites

- Python 3.11+
- [Claude Code](https://github.com/anthropics/claude-code) installed and authenticated
- Git
- `gh` CLI (for PR creation)

### Basic Usage

```bash
# Initialize a lazarus.yaml config
lazarus init

# Run a script with automatic healing
lazarus run ./scripts/my_script.sh

# Heal a specific failing script
lazarus heal ./scripts/broken_script.py

# Check prerequisites
lazarus check

# View healing history
lazarus history
```

### Configuration

Create a `lazarus.yaml` in your project root:

```yaml
version: "1"

scripts:
  - name: "data-sync"
    path: "./scripts/sync_data.py"
    schedule: "0 */6 * * *"  # Every 6 hours

healing:
  max_attempts: 3
  timeout_per_attempt: 300  # 5 minutes
  total_timeout: 900        # 15 minutes total

notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_success: true
    on_failure: true

git:
  create_pr: true
  branch_prefix: "lazarus/fix"
  draft_pr: false
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Script Fails│────▶│ Collect      │────▶│ Call Claude │
│             │     │ Context      │     │ Code        │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Notify      │◀────│ Create PR    │◀────│ Apply Fix   │
│ Users       │     │              │     │ & Verify    │
└─────────────┘     └──────────────┘     └─────────────┘
```

1. **Detection**: Script fails with non-zero exit code
2. **Context Collection**: Gather error output, script content, git history, environment info
3. **Redaction**: Remove secrets and sensitive data
4. **AI Analysis**: Send context to Claude Code for diagnosis and fix
5. **Verification**: Re-run script to confirm fix works
6. **PR Creation**: Create a pull request with the fix
7. **Notification**: Alert configured channels of the result

## GitHub Actions Integration

### Scheduled Healing

```yaml
# .github/workflows/lazarus-scheduled.yaml
name: Lazarus Scheduled Healing

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  heal:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run Lazarus
        run: lazarus run ./scripts/critical_job.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### On-Failure Healing

```yaml
# In your existing workflow
- name: Run Critical Script
  id: script
  run: ./scripts/critical_job.py
  continue-on-error: true

- name: Heal if Failed
  if: steps.script.outcome == 'failure'
  run: lazarus heal ./scripts/critical_job.py
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `lazarus heal <script>` | Attempt to heal a specific script |
| `lazarus run <script>` | Run script, automatically heal if it fails |
| `lazarus history` | View healing history and results |
| `lazarus validate` | Validate lazarus.yaml configuration |
| `lazarus init` | Create a new lazarus.yaml template |
| `lazarus check` | Check all prerequisites are installed |

## Documentation

- [Getting Started](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Self-Hosted Runner Setup](docs/self-hosted-runner.md)
- [Security](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Examples](docs/examples.md)
- [FAQ](docs/faq.md)

## Security

Lazarus takes security seriously:

- **Automatic Redaction**: Secrets and sensitive patterns are automatically redacted before AI analysis
- **Configurable Patterns**: Add custom redaction patterns for your environment
- **No Data Storage**: Context is only sent to Claude Code, never stored externally
- **Audit Logging**: All healing attempts are logged locally

See [SECURITY.md](SECURITY.md) for our security policy and how to report vulnerabilities.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [Claude Code](https://github.com/anthropics/claude-code) by Anthropic
- CLI powered by [Typer](https://typer.tiangolo.com/)
- Terminal output by [Rich](https://rich.readthedocs.io/)
