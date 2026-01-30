# Getting Started with Lazarus

A comprehensive guide to installing and running Lazarus for the first time.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [First Healing Walkthrough](#first-healing-walkthrough)
- [Next Steps](#next-steps)

---

## Prerequisites

Before installing Lazarus, ensure you have the following installed and configured:

### Required Software

**Python 3.11 or higher**
```bash
# Check your Python version
python --version  # Should be 3.11.0 or higher
```

**Claude Code CLI**
```bash
# Install Claude Code globally via npm
npm install -g @anthropic-ai/claude-code

# Authenticate with your Anthropic API key
claude login
```

**Git**
```bash
# Verify git is installed
git --version

# Configure git if not already done
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

**GitHub CLI (for PR creation)**
```bash
# macOS
brew install gh

# Linux
# See https://github.com/cli/cli/blob/trunk/docs/install_linux.md

# Authenticate with GitHub
gh auth login
```

### Environment Variables

Set the following environment variables:

```bash
# Required for Claude Code
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional: For notifications
export SLACK_WEBHOOK_URL="your-slack-webhook-url"
```

### Operating System Support

Lazarus is compatible with:
- macOS (10.15+)
- Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- Windows (via WSL2)

---

## Installation

### Option 1: Install via uv (Recommended)

```bash
# Install from PyPI using uv
uv pip install lazarus-heal

# Verify installation
lazarus --version
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/boriscardano/lazarus.git
cd lazarus

# Create a virtual environment (using uv - recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e .

# Or with pip
pip install -e .

# Verify installation
lazarus --version
```

### Option 3: Install with pipx (Isolated)

```bash
# Install pipx if not already installed
python -m pip install --user pipx
python -m pipx ensurepath

# Install Lazarus in isolated environment
pipx install lazarus-heal

# Verify installation
lazarus --version
```

### Verify Prerequisites

Run the prerequisite check to ensure everything is properly configured:

```bash
lazarus check
```

This will verify that `git`, `gh`, and `claude` are all available and properly configured.

---

## Quick Start

### Step 1: Initialize Configuration

Create a `lazarus.yaml` configuration file in your project root:

```bash
cd /path/to/your/project
lazarus init
```

This creates a minimal configuration template. Edit it to configure your scripts:

```yaml
# lazarus.yaml
scripts:
  - name: backup-database
    path: scripts/backup.py
    description: Daily database backup script
    timeout: 300

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900

git:
  create_pr: true
  branch_prefix: lazarus/fix

logging:
  level: INFO
  console: true
```

### Step 2: Run a Script with Healing

Try healing a script that might be failing:

```bash
lazarus heal scripts/your_script.py
```

Or use the `run` command (same behavior):

```bash
lazarus run scripts/your_script.py
```

### Step 3: Review the Results

Lazarus will:
1. Run your script and capture any failures
2. Build context including error output, git history, and system info
3. Request a fix from Claude Code
4. Verify the fix by re-running the script
5. Create a pull request with the fix (if enabled)
6. Display a summary of the healing process

---

## First Healing Walkthrough

Let's walk through a complete healing example with a failing script.

### Create a Test Script

Create a simple Python script with an intentional bug:

```bash
mkdir -p scripts
cat > scripts/hello.py << 'EOF'
#!/usr/bin/env python3
"""A simple script with a bug."""

def greet(name):
    print(f"Hello, {nam}!")  # Typo: 'nam' instead of 'name'

if __name__ == "__main__":
    greet("World")
EOF

chmod +x scripts/hello.py
```

### Configure Lazarus

Create a `lazarus.yaml`:

```yaml
scripts:
  - name: hello-script
    path: scripts/hello.py
    timeout: 60

healing:
  max_attempts: 2
  timeout_per_attempt: 120

git:
  create_pr: true
  branch_prefix: lazarus/fix

logging:
  level: INFO
  console: true
```

### Run Healing

Execute the healing process:

```bash
lazarus heal scripts/hello.py --verbose
```

You'll see output like:

```
┌─────────────────────────────────────────┐
│    Lazarus Self-Healing System          │
│  Script: /path/to/scripts/hello.py      │
│  Max attempts: 2                         │
│  Total timeout: 900s                     │
└─────────────────────────────────────────┘

⠋ Running healing process...

┌─────────────────────────────────────────┐
│         Healing Successful!              │
│  Attempts: 1                             │
│  Duration: 23.45s                        │
└─────────────────────────────────────────┘

Healing Attempts:
  Attempt 1: (23.45s)
    Claude: Fixed NameError by correcting variable name 'nam' to 'name'
    Status: success
    Files changed: scripts/hello.py
```

### Review the Pull Request

If PR creation is enabled, Lazarus creates a pull request:

```bash
# View the PR
gh pr view

# Or list all PRs
gh pr list
```

The PR includes:
- Clear title describing the fix
- Detailed description of what was fixed and why
- Changed files with diff
- Test results from verification

### View Healing History

Check the history of all healing sessions:

```bash
lazarus history
```

Output:

```
                    Healing History
┌────────────────┬──────────┬────────┬─────────┬──────────┬──────────┐
│ Timestamp      │ Script   │ Status │ Attempts│ Duration │ PR URL   │
├────────────────┼──────────┼────────┼─────────┼──────────┼──────────┤
│ 2026-01-30 ... │ hello.py │ Success│ 1       │ 23.5s    │ https:// │
└────────────────┴──────────┴────────┴─────────┴──────────┴──────────┘
```

---

## Next Steps

Now that you have Lazarus running, explore these topics:

### Configuration
- [Configuration Reference](configuration.md) - Complete guide to all configuration options
- [Examples](examples.md) - Real-world configuration examples

### Integration
- [GitHub Actions](github-actions.md) - Automate healing in CI/CD
- [Self-Hosted Runner Setup](self-hosted-runner.md) - Run Lazarus on your own infrastructure

### Advanced Topics
- [Architecture](architecture.md) - Understand how Lazarus works internally
- [Security](security.md) - Security best practices and threat model
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### CLI Commands
- `lazarus heal <script>` - Heal a specific failing script
- `lazarus run <script>` - Run a script with automatic healing
- `lazarus diagnose <script>` - Analyze a script without making changes (read-only)
- `lazarus history` - View healing history
- `lazarus validate` - Validate your configuration
- `lazarus init` - Create configuration template
- `lazarus check` - Verify prerequisites

### Community
- [GitHub Issues](https://github.com/boriscardano/lazarus/issues) - Report bugs or request features
- [Contributing Guide](../CONTRIBUTING.md) - Contribute to Lazarus
- [FAQ](faq.md) - Frequently asked questions
