# Lazarus Installation & Distribution Scripts

This directory contains scripts for installing, updating, and uninstalling Lazarus.

## Scripts Overview

### install.sh

Installation script that checks prerequisites and installs Lazarus.

**Features:**
- Checks Python 3.11+ and pip
- Verifies optional dependencies (Claude Code, gh CLI, git)
- Supports both user and development installations
- Colored output with clear status messages
- Validates installation after completion

**Usage:**

```bash
# Regular installation
./scripts/install.sh

# Development installation (editable mode)
./scripts/install.sh --dev

# Show help
./scripts/install.sh --help
```

**Installation Types:**

- **Regular**: Installs from PyPI or local source as a standard package
- **Development**: Installs in editable mode with dev dependencies for contributors

### uninstall.sh

Uninstallation script that removes Lazarus and optionally cleans up configuration files.

**Features:**
- Removes Lazarus package via pip
- Optionally removes user configuration and history
- Prompts for confirmation before removing data
- Works with all installation types (pip, source, dev)
- Clears shell command cache

**Usage:**

```bash
# Uninstall package only (keep config)
./scripts/uninstall.sh

# Uninstall and remove configuration
./scripts/uninstall.sh --remove-config

# Force uninstall without prompts
./scripts/uninstall.sh --remove-config --force

# Show help
./scripts/uninstall.sh --help
```

**Configuration Files:**
- `~/.lazarus/` - User configuration directory
- `~/.lazarus-history` - Healing history file
- `lazarus.yaml` - Project-level config (not removed)

### update.sh

Update script that upgrades Lazarus to the latest version.

**Features:**
- Auto-detects installation type (pip, source, or dev)
- Pulls latest changes from git for source installs
- Handles stashing uncommitted changes
- Runs migrations if needed
- Shows changelog highlights
- Verifies update success

**Usage:**

```bash
# Update with confirmation
./scripts/update.sh

# Force update without prompts
./scripts/update.sh --force

# Skip migrations
./scripts/update.sh --skip-migrations

# Show help
./scripts/update.sh --help
```

**Installation Types:**
- **pip**: Updates from PyPI using `pip install --upgrade`
- **source**: Pulls from git and reinstalls
- **dev**: Pulls from git (editable install remains editable)

### setup-workflows.sh

Workflow setup script that configures GitHub Actions workflows for automated healing.

**Features:**
- Validates git repository and workflow templates
- Interactive and non-interactive modes
- Customizable cron schedules and script paths
- Automatic backup of existing workflows
- Idempotent (safe to run multiple times)
- Detailed setup instructions and reminders

**Usage:**

```bash
# Interactive mode (prompts for options)
./scripts/setup-workflows.sh

# Install all workflows with defaults
./scripts/setup-workflows.sh --non-interactive --workflow all

# Install specific workflow
./scripts/setup-workflows.sh --workflow scheduled --schedule "0 */4 * * *"

# Custom configuration
./scripts/setup-workflows.sh --workflow manual --script-path "./src/app.py"

# Show help
./scripts/setup-workflows.sh --help
```

**Workflow Types:**
- **scheduled**: Runs healing on a cron schedule
- **on-failure**: Reusable workflow for healing failed scripts
- **manual**: On-demand healing with full parameter control
- **all**: Install all workflow types

**Post-Setup Requirements:**
- Add ANTHROPIC_API_KEY to GitHub Secrets
- Optionally add GH_TOKEN for PR/issue creation
- Configure self-hosted runner or modify workflows for GitHub-hosted runners

## Common Workflows

### First-Time Installation

```bash
# Clone repository (if not using pip)
git clone https://github.com/yourusername/lazarus.git
cd lazarus

# Install
./scripts/install.sh

# Verify installation
lazarus check
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/lazarus.git
cd lazarus

# Install in development mode
./scripts/install.sh --dev

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy src/lazarus
```

### Updating Lazarus

```bash
# Update to latest version
./scripts/update.sh

# Force update without confirmation
./scripts/update.sh --force
```

### Setting Up GitHub Workflows

```bash
# Interactive setup (recommended)
./scripts/setup-workflows.sh

# Quick setup with all workflows
./scripts/setup-workflows.sh --non-interactive --workflow all

# Setup scheduled healing only
./scripts/setup-workflows.sh --workflow scheduled
```

### Clean Uninstallation

```bash
# Remove everything including config
./scripts/uninstall.sh --remove-config

# Or force without prompts
./scripts/uninstall.sh --remove-config --force
```

## Platform Support

All scripts support:
- macOS (tested on macOS 10.15+)
- Linux (tested on Ubuntu 20.04+, Debian 11+)

**Not supported:**
- Windows (use WSL2 or install via pip directly)

## Prerequisites

### Required
- Bash 4.0+
- Python 3.11+
- pip package manager
- git

### Recommended
- Claude Code (required for healing functionality)
- gh CLI (required for PR creation)

## Color Output

All scripts use colored output for better readability:

- **Green**: Success messages
- **Red**: Error messages
- **Yellow**: Warning messages
- **Blue**: Informational messages

## Error Handling

All scripts:
- Use `set -e` to exit on errors
- Provide clear error messages
- Suggest next steps on failure
- Are idempotent where possible

## Exit Codes

- `0` - Success
- `1` - Error (generic)

## Testing Scripts

To test scripts without making changes:

```bash
# Test help output
./scripts/install.sh --help
./scripts/uninstall.sh --help
./scripts/update.sh --help

# Dry-run installation checks (stops before actual install)
# Edit script and comment out install_lazarus function call
```

## Troubleshooting

### Script not found

```bash
# Make sure scripts are executable
chmod +x scripts/*.sh
```

### Python version error

```bash
# Check Python version
python3 --version

# Upgrade Python if needed
# macOS: brew install python@3.12
# Ubuntu: sudo apt install python3.12
```

### Claude Code not found

```bash
# Install Claude Code
# See: https://github.com/anthropics/claude-code
```

### gh CLI not found

```bash
# Install gh CLI
# macOS: brew install gh
# Ubuntu: see https://cli.github.com/
```

### Update fails with git conflicts

```bash
# The script will offer to stash changes
# Or manually resolve:
git stash
./scripts/update.sh
git stash pop
```

## Contributing

When modifying scripts:

1. Test on both macOS and Linux
2. Ensure all exit codes are correct
3. Add error handling for new operations
4. Update help text and this README
5. Test with both --force and interactive modes
6. Verify colored output works correctly

## Security

Scripts follow these security practices:

- No automatic `sudo` elevation
- Clear confirmation prompts for destructive operations
- No execution of remote code without verification
- No storage of credentials
- Safe handling of git operations

## License

These scripts are part of Lazarus and are licensed under the MIT License.
