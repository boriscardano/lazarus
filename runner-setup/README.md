# Self-Hosted Runner Setup

This directory contains comprehensive guides and scripts for setting up GitHub Actions self-hosted runners with Lazarus integration.

## Quick Start

### macOS

```bash
# 1. Install runner
./scripts/install-runner.sh

# 2. Configure as service (optional)
./scripts/configure-launchd.sh

# 3. Install Claude Code
pip3 install claude-code
claude auth login

# 4. Verify everything is working
./scripts/check-runner-health.sh
```

### Linux

```bash
# 1. Install runner
./scripts/install-runner.sh

# 2. Configure as service (optional)
sudo ./scripts/configure-systemd.sh

# 3. Install Claude Code
pip3 install claude-code
claude auth login

# 4. Verify everything is working
./scripts/check-runner-health.sh
```

## Documentation

Detailed setup guides are available for each platform:

- **[macOS Setup Guide](docs/macos-guide.md)** - Complete guide for macOS including:
  - Prerequisites and system requirements
  - Runner installation and configuration
  - LaunchAgent service setup
  - Security considerations
  - Troubleshooting guide

- **[Linux Setup Guide](docs/linux-guide.md)** - Complete guide for Linux including:
  - Prerequisites for Ubuntu/Debian and RHEL/CentOS
  - Runner installation and configuration
  - systemd service setup
  - Security hardening
  - Monitoring and logging
  - Troubleshooting guide

## Scripts

All scripts include colored output, error handling, and interactive prompts. They can be run individually or as part of the automated setup process.

### Installation Scripts

#### install-runner.sh

Cross-platform runner installation script that detects your OS and architecture.

```bash
./scripts/install-runner.sh
```

**Features:**
- Automatic OS and architecture detection
- Interactive repository and token configuration
- Optional GitHub CLI integration for token generation
- Automatic service setup prompt
- Comprehensive validation and error checking

#### configure-launchd.sh (macOS)

Creates and configures a LaunchAgent to run the runner as a background service on macOS.

```bash
./scripts/configure-launchd.sh
```

**Features:**
- Automatic PATH and environment detection
- Environment file integration
- Auto-start on login configuration
- Optional system-wide LaunchDaemon setup
- Service validation and status checking

#### configure-systemd.sh (Linux)

Creates and configures a systemd service to run the runner on Linux.

```bash
sudo ./scripts/configure-systemd.sh
```

**Features:**
- Dedicated user setup
- Resource limit configuration
- Security hardening options
- SELinux/AppArmor support
- Firewall configuration
- Log rotation setup

### Maintenance Scripts

#### check-runner-health.sh

Comprehensive health check script that verifies all components.

```bash
./scripts/check-runner-health.sh
```

**Checks:**
- Runner installation and configuration
- Runner process status
- Service status (LaunchAgent/systemd)
- Claude Code installation and authentication
- GitHub CLI authentication
- Disk space usage
- Network connectivity
- Environment configuration
- Python environment
- Recent logs for errors

**Output:**
- Color-coded status indicators
- Health score calculation
- Detailed diagnostics
- Exit code for automation (0 = healthy, 1 = issues)

#### update-runner.sh

Safe update script for runner binary, Lazarus, and Claude Code.

```bash
./scripts/update-runner.sh [OPTIONS]
```

**Options:**
- `--dry-run` - Show what would be updated without making changes
- `--skip-runner` - Skip runner binary update
- `--skip-lazarus` - Skip Lazarus update
- `--skip-claude` - Skip Claude Code update
- `-y, --yes` - Automatic yes to prompts
- `-h, --help` - Show help message

**Features:**
- Version checking for all components
- Automatic backup creation
- Safe service stop/start
- Update verification
- Automatic cleanup of old backups
- Rollback instructions

## Usage Examples

### Initial Setup

Complete setup from scratch:

```bash
# Clone Lazarus
git clone https://github.com/YOUR_ORG/lazarus.git
cd lazarus/runner-setup

# Run installation
./scripts/install-runner.sh

# Follow prompts to:
# - Enter repository URL
# - Enter registration token (or auto-generate with gh CLI)
# - Configure runner name and labels
# - Set up as system service
# - Test the runner
```

### Daily Monitoring

Check runner health daily:

```bash
# Run health check
./scripts/check-runner-health.sh

# Or add to crontab for automated checks
crontab -e
# Add: 0 9 * * * /path/to/lazarus/runner-setup/scripts/check-runner-health.sh
```

### Regular Updates

Update runner and components:

```bash
# Check what would be updated
./scripts/update-runner.sh --dry-run

# Perform update interactively
./scripts/update-runner.sh

# Or non-interactively
./scripts/update-runner.sh -y

# Update only Claude Code
./scripts/update-runner.sh --skip-runner --skip-lazarus
```

### Service Management

#### macOS

```bash
# Start runner
launchctl start com.github.actions.runner

# Stop runner
launchctl stop com.github.actions.runner

# Check status
launchctl list | grep github.actions.runner

# View logs
tail -f ~/actions-runner/runner.log

# Reload configuration
launchctl unload ~/Library/LaunchAgents/com.github.actions.runner.plist
launchctl load ~/Library/LaunchAgents/com.github.actions.runner.plist
```

#### Linux

```bash
# Start runner
sudo systemctl start actions-runner

# Stop runner
sudo systemctl stop actions-runner

# Restart runner
sudo systemctl restart actions-runner

# Check status
sudo systemctl status actions-runner

# View logs
sudo journalctl -u actions-runner -f

# Enable auto-start
sudo systemctl enable actions-runner

# Reload configuration
sudo systemctl daemon-reload
sudo systemctl restart actions-runner
```

## Directory Structure

```
runner-setup/
├── README.md                       # This file
├── docs/
│   ├── macos-guide.md             # Comprehensive macOS setup guide
│   └── linux-guide.md             # Comprehensive Linux setup guide
└── scripts/
    ├── install-runner.sh          # Cross-platform installation
    ├── configure-launchd.sh       # macOS LaunchAgent setup
    ├── configure-systemd.sh       # Linux systemd service setup
    ├── check-runner-health.sh     # Health check and diagnostics
    └── update-runner.sh           # Update runner and components
```

## Requirements

### All Platforms

- curl
- tar
- git (recommended)
- jq (recommended)
- GitHub CLI (recommended)

### macOS Specific

- macOS 11.0 (Big Sur) or later
- Xcode Command Line Tools
- Homebrew (recommended)

### Linux Specific

- Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / CentOS 8+
- systemd
- sudo access

## Security Considerations

### API Keys

- Store API keys in `~/.config/lazarus/env` with 600 permissions
- Never commit API keys to version control
- Rotate keys regularly
- Monitor usage in Anthropic dashboard

### Runner Permissions

- Use dedicated user account for runner (Linux)
- Limit runner permissions (don't grant sudo)
- Keep runner and system updated
- Review workflows before execution

### Network Security

- Configure firewall rules for GitHub IP ranges
- Use HTTPS for all communications
- Monitor network activity
- Set up proxy if behind corporate firewall

### File System Security

- Secure runner directory (700 permissions)
- Secure configuration files (600 permissions)
- Enable SELinux/AppArmor on Linux
- Regular security audits

## Troubleshooting

### Runner Won't Start

1. Check service status
2. Review logs for errors
3. Verify runner registration
4. Check file permissions
5. Ensure network connectivity

### Authentication Issues

1. Verify API key is set
2. Re-authenticate Claude Code
3. Check environment file permissions
4. Verify service loads environment

### Performance Issues

1. Check disk space
2. Monitor CPU/memory usage
3. Review concurrent job limits
4. Clean old workflow data

### Network Issues

1. Verify GitHub connectivity
2. Check firewall rules
3. Test API access
4. Review proxy settings

## Support

For detailed troubleshooting:

1. Review the platform-specific guide ([macOS](docs/macos-guide.md) or [Linux](docs/linux-guide.md))
2. Run health check: `./scripts/check-runner-health.sh`
3. Check logs (see service management commands above)
4. Open an issue in the Lazarus repository
5. Consult [GitHub Actions documentation](https://docs.github.com/en/actions/hosting-your-own-runners)

## Maintenance Schedule

### Daily
- Monitor runner status
- Check disk space

### Weekly
- Review logs for errors
- Verify authentication
- Check for failed workflows

### Monthly
- Update runner binary
- Update dependencies
- Clean old workflow data
- Review security logs

### Quarterly
- Update OS and security patches
- Rotate API keys
- Review and update configuration
- Test disaster recovery

## Contributing

When adding new features or scripts:

1. Follow the existing script structure
2. Include colored output and error handling
3. Add proper documentation
4. Test on both macOS and Linux
5. Update this README

## License

This project is licensed under the MIT License - see the LICENSE file for details.
