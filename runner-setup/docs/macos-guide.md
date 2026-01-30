# macOS Self-Hosted Runner Setup Guide

This guide walks you through setting up a self-hosted GitHub Actions runner on macOS with Lazarus installed.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installing GitHub Actions Runner](#installing-github-actions-runner)
3. [Installing Claude Code](#installing-claude-code)
4. [Creating a LaunchAgent Service](#creating-a-launchagent-service)
5. [Security Considerations](#security-considerations)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:

### System Requirements

- macOS 11.0 (Big Sur) or later
- At least 4GB RAM (8GB+ recommended)
- 20GB+ free disk space
- Admin access to the machine

### Required Tools

1. **Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

2. **Homebrew** (package manager)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **GitHub CLI** (optional but recommended)
   ```bash
   brew install gh
   gh auth login
   ```

### GitHub Requirements

- A GitHub repository with Actions enabled
- Admin access to the repository
- A Personal Access Token (PAT) with `repo` scope (for private repos) or `public_repo` (for public repos)

## Installing GitHub Actions Runner

### 1. Create Runner Directory

```bash
mkdir -p ~/actions-runner
cd ~/actions-runner
```

### 2. Download the Latest Runner

Visit your repository's Settings > Actions > Runners > New self-hosted runner, or use:

```bash
# For macOS ARM64 (M1/M2/M3)
curl -o actions-runner-osx-arm64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-osx-arm64-2.313.0.tar.gz

# For macOS x64 (Intel)
curl -o actions-runner-osx-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-osx-x64-2.313.0.tar.gz

# Extract
tar xzf ./actions-runner-osx-*.tar.gz
rm ./actions-runner-osx-*.tar.gz
```

### 3. Configure the Runner

```bash
# Generate a registration token from GitHub
# Settings > Actions > Runners > New self-hosted runner

./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# You'll be prompted for:
# - Runner name (default: hostname)
# - Runner group (default: Default)
# - Labels (default: self-hosted,macOS,ARM64 or X64)
# - Work folder (default: _work)
```

### 4. Test the Runner

```bash
./run.sh
# Press Ctrl+C to stop after verifying it connects
```

## Installing Claude Code

### 1. Install Claude Code CLI

```bash
# Install via pip (recommended)
pip3 install claude-code

# Or install from source
git clone https://github.com/anthropics/claude-code.git
cd claude-code
pip3 install -e .
```

### 2. Authenticate Claude Code

```bash
# Login with your Anthropic API key
claude auth login

# Verify authentication
claude auth status
```

### 3. Configure for Automation

Store your API key securely:

```bash
# Create a secure location for credentials
mkdir -p ~/.config/lazarus
chmod 700 ~/.config/lazarus

# Store API key (will be used by the service)
echo "ANTHROPIC_API_KEY=your_api_key_here" > ~/.config/lazarus/env
chmod 600 ~/.config/lazarus/env
```

## Creating a LaunchAgent Service

### 1. Create LaunchAgent Configuration

Use the provided script or create manually:

```bash
# Using the provided script
cd /path/to/lazarus/runner-setup/scripts
./configure-launchd.sh
```

Or create manually:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.actions.runner</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/actions-runner/run.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/actions-runner/runner.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/actions-runner/runner-error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>/Users/YOUR_USERNAME</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/actions-runner</string>

    <key>SessionCreate</key>
    <true/>
</dict>
</plist>
```

Save to: `~/Library/LaunchAgents/com.github.actions.runner.plist`

### 2. Load and Start the Service

```bash
# Load the LaunchAgent
launchctl load ~/Library/LaunchAgents/com.github.actions.runner.plist

# Start the service
launchctl start com.github.actions.runner

# Check status
launchctl list | grep github.actions.runner
```

### 3. Enable Auto-Start on Boot

The LaunchAgent with `RunAtLoad` set to `true` will automatically start on user login.

To start on system boot (not just user login), you would need to use a LaunchDaemon instead (requires sudo).

### 4. Verify Service is Running

```bash
# Check process
ps aux | grep "actions-runner"

# Check logs
tail -f ~/actions-runner/runner.log

# Use health check script
/path/to/lazarus/runner-setup/scripts/check-runner-health.sh
```

## Security Considerations

### 1. User Permissions

- **Run as dedicated user**: Create a dedicated user account for the runner
  ```bash
  sudo dscl . -create /Users/actions-runner
  sudo dscl . -create /Users/actions-runner UserShell /bin/bash
  sudo dscl . -create /Users/actions-runner RealName "GitHub Actions Runner"
  sudo dscl . -create /Users/actions-runner UniqueID 503
  sudo dscl . -create /Users/actions-runner PrimaryGroupID 20
  sudo dscl . -create /Users/actions-runner NFSHomeDirectory /Users/actions-runner
  ```

- **Limit permissions**: Don't give the runner user admin rights
- **Separate home directory**: Keep runner files isolated

### 2. API Key Security

- **Never commit API keys** to version control
- **Use environment files** with restricted permissions (chmod 600)
- **Rotate keys regularly**: Update API keys every 90 days
- **Monitor usage**: Track API key usage in Anthropic dashboard

### 3. Network Security

- **Firewall rules**: Ensure only necessary ports are open
- **HTTPS only**: All GitHub communications use HTTPS
- **Proxy support**: Configure if behind corporate firewall
  ```bash
  export https_proxy=http://proxy.example.com:8080
  ```

### 4. File System Security

```bash
# Secure runner directory
chmod 700 ~/actions-runner

# Secure logs
chmod 600 ~/actions-runner/*.log

# Secure configuration
chmod 600 ~/.config/lazarus/env
```

### 5. Update Management

- **Keep runner updated**: Use the update script regularly
- **Monitor security advisories**: Subscribe to GitHub Actions security updates
- **Patch macOS**: Keep OS up to date with security patches

### 6. Workflow Security

- **Review workflows**: Always review workflows before running
- **Limit secrets**: Only expose necessary secrets to workflows
- **Use workflow approval**: Enable required approvals for external contributors
- **Audit logs**: Regularly review runner execution logs

## Troubleshooting

### Runner Won't Start

**Problem**: LaunchAgent fails to start runner

**Solution**:
```bash
# Check LaunchAgent syntax
plutil -lint ~/Library/LaunchAgents/com.github.actions.runner.plist

# Unload and reload
launchctl unload ~/Library/LaunchAgents/com.github.actions.runner.plist
launchctl load ~/Library/LaunchAgents/com.github.actions.runner.plist

# Check system logs
log show --predicate 'processImagePath contains "actions-runner"' --last 1h
```

### Runner Keeps Disconnecting

**Problem**: Runner shows as offline frequently

**Solution**:
```bash
# Check network connectivity
ping github.com

# Verify runner token is valid
cd ~/actions-runner
./config.sh remove  # Remove old registration
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token NEW_TOKEN

# Check for resource issues
top -l 1 | grep -E "(Processes|CPU|PhysMem)"
```

### Claude Code Authentication Fails

**Problem**: Claude Code not authenticated in workflows

**Solution**:
```bash
# Verify API key is set
source ~/.config/lazarus/env
echo $ANTHROPIC_API_KEY

# Re-authenticate
claude auth logout
claude auth login

# Ensure environment is loaded in LaunchAgent
# Add to plist EnvironmentVariables section
```

### Permission Denied Errors

**Problem**: Runner can't execute scripts or access files

**Solution**:
```bash
# Check file permissions
ls -la ~/actions-runner/

# Fix permissions
chmod +x ~/actions-runner/*.sh
chmod 600 ~/actions-runner/.credentials*

# Check user context
whoami  # Should match LaunchAgent user
```

### Disk Space Issues

**Problem**: Runner fails due to lack of disk space

**Solution**:
```bash
# Check disk usage
df -h

# Clean old workflow data
cd ~/actions-runner/_work
find . -type d -mtime +7 -exec rm -rf {} +

# Clean runner cache
rm -rf ~/actions-runner/_diag/*

# Set up automatic cleanup in workflow
```

### High CPU Usage

**Problem**: Runner consuming excessive CPU

**Solution**:
```bash
# Check what's using CPU
top -o cpu

# Review concurrent job settings
# Edit .runner file to limit concurrent jobs

# Check for runaway processes
ps aux | grep actions-runner
```

### Logs Not Appearing

**Problem**: Can't find runner logs

**Solution**:
```bash
# Check log paths in plist
cat ~/Library/LaunchAgents/com.github.actions.runner.plist | grep -A 1 "Log"

# Create log directory if missing
mkdir -p ~/actions-runner/logs

# Check Console app for system logs
open -a Console

# Enable verbose logging
# Add to runner environment: ACTIONS_RUNNER_PRINT_LOG_TO_STDOUT=1
```

### Runner Registration Token Expired

**Problem**: Can't configure runner - token expired

**Solution**:
```bash
# Tokens expire after 1 hour
# Generate new token from GitHub:
# Settings > Actions > Runners > New self-hosted runner

# Or use GitHub CLI
gh api repos/OWNER/REPO/actions/runners/registration-token | jq -r .token
```

## Maintenance Tasks

### Daily

- Monitor runner status via GitHub UI
- Check disk space usage

### Weekly

- Review runner logs for errors
- Verify Claude Code authentication
- Check for failed workflows

### Monthly

- Update runner binary
- Update Claude Code
- Rotate API keys (if policy requires)
- Review security logs
- Clean up old workflow data

### Quarterly

- Update macOS and security patches
- Review and update firewall rules
- Audit runner permissions
- Test disaster recovery procedures

## Useful Commands

```bash
# Start/Stop/Restart runner
launchctl start com.github.actions.runner
launchctl stop com.github.actions.runner
launchctl unload ~/Library/LaunchAgents/com.github.actions.runner.plist
launchctl load ~/Library/LaunchAgents/com.github.actions.runner.plist

# View logs
tail -f ~/actions-runner/runner.log
tail -f ~/actions-runner/runner-error.log

# Check runner status
launchctl list | grep github.actions.runner

# Health check
/path/to/lazarus/runner-setup/scripts/check-runner-health.sh

# Update runner
/path/to/lazarus/runner-setup/scripts/update-runner.sh
```

## Additional Resources

- [GitHub Actions Self-Hosted Runner Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Lazarus GitHub Repository](https://github.com/YOUR_ORG/lazarus)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Apple LaunchAgents Documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)

## Support

If you encounter issues not covered in this guide:

1. Check the [GitHub Actions Community Forum](https://github.community/c/github-actions)
2. Open an issue in the Lazarus repository
3. Contact your organization's DevOps team
