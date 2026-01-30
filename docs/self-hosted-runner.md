# Self-Hosted Runner Setup

Guide for setting up GitHub self-hosted runners to execute Lazarus workflows.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Platform-Specific Guides](#platform-specific-guides)
- [Configuration](#configuration)
- [Running Lazarus](#running-lazarus)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Overview

Self-hosted runners enable you to run Lazarus workflows on your own infrastructure with full control over the environment.

**Why Self-Hosted Runners?**

- **Cost Control** - Avoid GitHub Actions minutes charges
- **Custom Environment** - Install specific tools and dependencies
- **Security** - Keep workflows on private infrastructure
- **Performance** - Use more powerful hardware
- **Local Network Access** - Connect to internal services

**Architecture:**
```
Your Infrastructure
  ├── Runner 1 (macOS)
  ├── Runner 2 (Linux)
  └── Runner 3 (Linux)
       │
       ├─→ Receives GitHub workflow jobs
       ├─→ Runs Lazarus
       ├─→ Creates PRs
       └─→ Sends notifications
```

**Use Cases:**
1. **Scheduled maintenance** - Daily/weekly script healing
2. **On-failure healing** - Automatic fixes when scripts break
3. **Production deployments** - Safe automated fixes before deployment
4. **Multi-repo automation** - Centralized healing across projects

---

## Quick Start

### 1. Choose Your Platform

- **macOS?** → See [macOS Guide](../runner-setup/docs/macos-guide.md)
- **Linux?** → See [Linux Guide](../runner-setup/docs/linux-guide.md)
- **Windows?** → Use WSL2 and follow Linux guide

### 2. Minimal Setup (5 minutes)

```bash
# 1. Install GitHub runner
mkdir -p ~/actions-runner
cd ~/actions-runner
curl -s https://raw.githubusercontent.com/actions/runner/main/...  # See OS-specific guide

# 2. Register with GitHub
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# 3. Install Lazarus
pip install lazarus-heal

# 4. Authenticate
claude auth login
gh auth login

# 5. Start runner
./run.sh  # Or use systemd/launchd for background
```

### 3. Enable in Workflow

```yaml
jobs:
  heal:
    runs-on: self-hosted  # Use your runner
    steps:
      - uses: actions/checkout@v3
      - run: lazarus run ./scripts/*.py
```

---

## Platform-Specific Guides

### macOS Setup

For complete macOS installation with launchd service:

**See:** [macOS Self-Hosted Runner Guide](../runner-setup/docs/macos-guide.md)

**Key sections:**
- System requirements (11.0+, 4GB+ RAM)
- GitHub Actions runner installation
- Claude Code setup
- LaunchAgent service creation
- Security configuration
- Troubleshooting (disconnects, auth issues, etc.)

**Quick reference:**
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download and configure
curl -o actions-runner-osx-arm64.tar.gz -L https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-osx-arm64-2.313.0.tar.gz
tar xzf ./actions-runner-osx-arm64.tar.gz

# Configure (replace with your values)
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Install Claude Code
pip3 install claude-code

# Set up LaunchAgent (use provided script)
cd /path/to/lazarus/runner-setup/scripts
./configure-launchd.sh

# Start service
launchctl start com.github.actions.runner
```

### Linux Setup

For complete Linux installation with systemd service:

**See:** [Linux Self-Hosted Runner Guide](../runner-setup/docs/linux-guide.md)

**Key sections:**
- OS support (Ubuntu, Debian, RHEL, CentOS)
- Package installation
- Runner setup as dedicated user
- systemd service creation
- Security hardening (SELinux, AppArmor, firewall)
- Log rotation and monitoring
- Troubleshooting (service issues, disk space, etc.)

**Quick reference:**
```bash
# Ubuntu/Debian prerequisites
sudo apt update && sudo apt install -y curl wget git python3 python3-pip

# Create runner user
sudo useradd -m -s /bin/bash actions-runner
sudo su - actions-runner

# Download runner
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-linux-x64-2.313.0.tar.gz
tar xzf ./actions-runner-linux-x64.tar.gz
rm ./actions-runner-linux-x64.tar.gz

# Configure
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Install Claude Code
python3 -m venv ~/claude-env
source ~/claude-env/bin/activate
pip install claude-code

# Set up systemd service (use provided script)
exit  # Back to your user
cd /path/to/lazarus/runner-setup/scripts
sudo ./configure-systemd.sh

# Start service
sudo systemctl start actions-runner
```

---

## Configuration

### Workflow Configuration

Create a GitHub Actions workflow to run Lazarus:

```yaml
name: Auto-Heal Failing Scripts

on:
  schedule:
    # Daily at 2 AM
    - cron: "0 2 * * *"

  # Manual trigger
  workflow_dispatch:
    inputs:
      script:
        description: "Script to heal"
        required: false
        default: "scripts/*.py"

jobs:
  heal:
    runs-on: self-hosted  # Use your self-hosted runner

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Run Lazarus
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          lazarus run ./scripts/your_script.py
```

### Environment Variables

Set up required environment variables on your runner:

```bash
# Store API key securely (on runner host)
mkdir -p ~/.config/lazarus
cat > ~/.config/lazarus/env << 'EOF'
export ANTHROPIC_API_KEY="your-api-key"
export GH_TOKEN="your-github-token"
export SLACK_WEBHOOK_URL="optional-slack-webhook"
EOF

chmod 600 ~/.config/lazarus/env

# Source before running workflows
source ~/.config/lazarus/env
```

Or configure in GitHub Actions secrets:

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Triggering Workflows

**Scheduled healing:**
```yaml
on:
  schedule:
    - cron: "0 2 * * *"    # Daily 2 AM
    - cron: "0 */6 * * *"  # Every 6 hours
    - cron: "0 0 * * 1"    # Weekly Monday midnight
```

**On failure detection:**
```yaml
on:
  workflow_run:
    workflows: [main-tests]
    types: [completed]
```

**Manual trigger:**
```yaml
on:
  workflow_dispatch:
    inputs:
      script:
        required: true
```

---

## Running Lazarus

### Basic Workflow

```yaml
jobs:
  heal:
    runs-on: self-hosted

    steps:
      - uses: actions/checkout@v3

      - name: Heal scripts
        run: |
          lazarus run ./scripts/*.py

      - name: Show results
        if: always()
        run: |
          lazarus history
          gh pr list --limit 1
```

### Advanced Workflow

```yaml
jobs:
  heal:
    runs-on: self-hosted
    timeout-minutes: 60

    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Heal scripts
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Heal multiple scripts
          lazarus run ./scripts/sync.py
          lazarus run ./scripts/backup.sh
          lazarus run ./scripts/deploy.js

      - name: Notify on completion
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
          text: "Lazarus healing completed"
          fields: repo,message,commit
```

---

## Monitoring

### Health Check

Use the provided health check script:

```bash
# macOS
/path/to/lazarus/runner-setup/scripts/check-runner-health.sh

# Output includes:
# - Runner status (online/offline)
# - Last job completion time
# - Available disk space
# - CPU/Memory usage
```

### Viewing Logs

**macOS:**
```bash
# View logs in real-time
tail -f ~/actions-runner/runner.log

# Or use Console.app
open -a Console
```

**Linux:**
```bash
# View systemd logs
sudo journalctl -u actions-runner -f

# Recent logs
sudo journalctl -u actions-runner -n 100

# Since specific time
sudo journalctl -u actions-runner --since "1 hour ago"
```

### Metrics Collection

For monitoring runner health:

```bash
# Check disk usage
df -h ~/actions-runner/_work

# Check memory
free -h  # Linux
vm_stat  # macOS

# Check running processes
ps aux | grep -E "claude|actions-runner"

# Check network connectivity
ping github.com
ping api.anthropic.com
```

---

## Troubleshooting

### Runner Status Issues

**Runner shows offline:**
```bash
# Restart the runner
# macOS
launchctl stop com.github.actions.runner
launchctl start com.github.actions.runner

# Linux
sudo systemctl restart actions-runner

# Check status
launchctl list | grep github.actions.runner  # macOS
sudo systemctl status actions-runner          # Linux
```

**Runner registration token expired:**
Generate a new token from GitHub:
- Settings > Actions > Runners > New self-hosted runner
- Run `./config.sh` again with new token

### Lazarus Issues

**Lazarus command not found:**
```bash
# Install Lazarus
pip install lazarus-heal

# Or activate virtual environment
source ~/claude-env/bin/activate

# Verify installation
lazarus --version
```

**Claude Code authentication fails:**
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Re-authenticate
claude auth logout
claude auth login

# Verify
claude auth status
```

**PR creation fails:**
```bash
# Check GitHub CLI auth
gh auth status

# Check token permissions
gh api user

# Re-authenticate
gh auth logout
gh auth login
```

### Common Problems

See detailed troubleshooting in the platform-specific guides:
- [macOS Troubleshooting](../runner-setup/docs/macos-guide.md#troubleshooting)
- [Linux Troubleshooting](../runner-setup/docs/linux-guide.md#troubleshooting)

---

## Helper Scripts

The `runner-setup/scripts/` directory contains useful utilities:

```bash
# Check runner health
./runner-setup/scripts/check-runner-health.sh

# Update runner binary
./runner-setup/scripts/update-runner.sh

# Configure systemd service (Linux)
sudo ./runner-setup/scripts/configure-systemd.sh

# Configure launchd service (macOS)
./runner-setup/scripts/configure-launchd.sh
```

---

## Next Steps

1. **Choose your platform:** macOS or Linux
2. **Follow platform guide:** [macOS](../runner-setup/docs/macos-guide.md) or [Linux](../runner-setup/docs/linux-guide.md)
3. **Create a workflow:** Use examples above
4. **Test it:** Manually trigger workflow first
5. **Monitor health:** Check runner logs regularly
6. **Update regularly:** Keep runner and Lazarus current

---

## Resources

- [GitHub Actions Runner Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [macOS Self-Hosted Runner Guide](../runner-setup/docs/macos-guide.md)
- [Linux Self-Hosted Runner Guide](../runner-setup/docs/linux-guide.md)
- [Lazarus Configuration Reference](configuration.md)
- [GitHub Actions Integration](github-actions.md)

## Support

For issues:
1. Check the platform-specific troubleshooting guide
2. Review runner logs
3. Verify authentication (claude, gh, git)
4. Check network connectivity
5. Open an issue on GitHub
