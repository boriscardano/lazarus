# Lazarus Quick Start Guide

Get up and running with Lazarus in 5 minutes.

## 1. Install Lazarus

### Option A: From PyPI (Recommended for Users)

```bash
pip install lazarus-heal
```

### Option B: From Source (Recommended for Contributors)

```bash
# Clone the repository
git clone https://github.com/yourusername/lazarus.git
cd lazarus

# Run the installation script
./scripts/install.sh

# Or for development mode
./scripts/install.sh --dev
```

## 2. Install Prerequisites

Lazarus requires Claude Code for AI-powered healing:

```bash
# Install Claude Code
# See: https://github.com/anthropics/claude-code

# Authenticate with your API key
claude auth
```

For PR creation, install the GitHub CLI:

```bash
# macOS
brew install gh

# Linux
# See: https://cli.github.com/

# Authenticate
gh auth login
```

## 3. Verify Installation

```bash
# Check that everything is working
lazarus check

# You should see:
# ✓ Python 3.11+
# ✓ Claude Code
# ✓ gh CLI
# ✓ Git
```

## 4. Initialize Configuration

```bash
# Create a lazarus.yaml in your project
lazarus init

# This creates a template configuration file
```

Edit `lazarus.yaml` to configure your scripts and notifications:

```yaml
version: "1"

scripts:
  - name: "my-script"
    path: "./scripts/my_script.sh"
    schedule: "0 */6 * * *"

healing:
  max_attempts: 3
  timeout_per_attempt: 300

notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_failure: true

git:
  create_pr: true
  branch_prefix: "lazarus/fix"
```

## 5. Run Your First Healing

### Option A: Run a script with automatic healing

```bash
# Lazarus will run the script and heal it if it fails
lazarus run ./scripts/my_script.sh
```

### Option B: Heal an existing failing script

```bash
# Run this on a script you know is failing
lazarus heal ./scripts/broken_script.py
```

## 6. What Happens During Healing

1. **Script Execution**: Lazarus runs your script
2. **Error Detection**: If it fails, error context is collected
3. **AI Analysis**: Claude Code analyzes the error
4. **Fix Application**: The AI suggests and applies fixes
5. **Verification**: The script is re-run to verify the fix
6. **PR Creation**: A pull request is created with the fix
7. **Notification**: You're notified via configured channels

## 7. View Healing History

```bash
# See all healing attempts
lazarus history

# View details of a specific healing
lazarus history <healing-id>
```

## 8. Common Workflows

### Schedule Healing in GitHub Actions

Create `.github/workflows/lazarus.yaml`:

```yaml
name: Lazarus Scheduled Healing

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  heal:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Lazarus
        run: pip install lazarus-heal

      - name: Run healing
        run: lazarus run ./scripts/critical_job.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Heal on Failure

```yaml
- name: Run Critical Script
  id: script
  run: ./scripts/critical_job.py
  continue-on-error: true

- name: Heal if Failed
  if: steps.script.outcome == 'failure'
  run: lazarus heal ./scripts/critical_job.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Self-Hosted Runner

For running Lazarus continuously on your own infrastructure:

```bash
# See detailed setup guides
cat docs/self-hosted-runner-macos.md
cat docs/self-hosted-runner-linux.md
```

## 9. Configuration Reference

See [docs/configuration.md](docs/configuration.md) for complete configuration options:

- Script execution settings
- Healing behavior
- Notification channels
- Git and PR settings
- Security options

## 10. Troubleshooting

### Command not found

```bash
# Make sure pip's bin directory is in your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Claude Code not working

```bash
# Check authentication
claude --version

# Re-authenticate if needed
claude auth
```

### PR creation fails

```bash
# Check gh CLI authentication
gh auth status

# Re-authenticate if needed
gh auth login
```

### Script healing fails

```bash
# Check logs
lazarus history

# Validate configuration
lazarus validate

# Increase timeout for complex fixes
# Edit lazarus.yaml and increase timeout_per_attempt
```

## Next Steps

- Read [docs/architecture.md](docs/architecture.md) to understand how Lazarus works
- Explore [examples/](examples/) for common use cases
- Check [docs/security.md](docs/security.md) for security best practices
- See [CONTRIBUTING.md](CONTRIBUTING.md) to contribute to Lazarus

## Getting Help

- Documentation: [docs/](docs/)
- Issues: https://github.com/yourusername/lazarus/issues
- Discussions: https://github.com/yourusername/lazarus/discussions

## Updating Lazarus

```bash
# Update to latest version
./scripts/update.sh

# Or via pip
pip install --upgrade lazarus-heal
```

## Uninstalling

```bash
# Keep configuration
./scripts/uninstall.sh

# Remove everything
./scripts/uninstall.sh --remove-config
```

---

**That's it!** You now have Lazarus set up and ready to automatically heal your failing scripts.

For more detailed information, see the [full documentation](docs/) or run `lazarus --help`.
