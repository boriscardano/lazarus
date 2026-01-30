# Linux Self-Hosted Runner Setup Guide

This guide walks you through setting up a self-hosted GitHub Actions runner on Linux with Lazarus installed.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installing GitHub Actions Runner](#installing-github-actions-runner)
3. [Installing Claude Code](#installing-claude-code)
4. [Creating a systemd Service](#creating-a-systemd-service)
5. [Security Hardening](#security-hardening)
6. [Monitoring and Logs](#monitoring-and-logs)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / CentOS 8+
- At least 4GB RAM (8GB+ recommended)
- 20GB+ free disk space
- Sudo access

### For Ubuntu/Debian

```bash
# Update package lists
sudo apt update

# Install required packages
sudo apt install -y \
    curl \
    wget \
    git \
    jq \
    libssl-dev \
    libffi-dev \
    python3 \
    python3-pip \
    python3-venv

# Install GitHub CLI (optional but recommended)
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
    https://cli.github.com/packages stable main" | \
    sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# Authenticate
gh auth login
```

### For RHEL/CentOS/Fedora

```bash
# Update packages
sudo dnf update -y

# Install required packages
sudo dnf install -y \
    curl \
    wget \
    git \
    jq \
    openssl-devel \
    libffi-devel \
    python3 \
    python3-pip

# Install GitHub CLI
sudo dnf install 'dnf-command(config-manager)' -y
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
sudo dnf install gh -y

# Authenticate
gh auth login
```

### GitHub Requirements

- A GitHub repository with Actions enabled
- Admin access to the repository
- A Personal Access Token (PAT) with `repo` scope

## Installing GitHub Actions Runner

### 1. Create Dedicated User

```bash
# Create runner user without login shell
sudo useradd -m -s /bin/bash actions-runner

# Optional: Add to docker group if running containers
# sudo usermod -aG docker actions-runner
```

### 2. Create Runner Directory

```bash
# Switch to runner user
sudo su - actions-runner

# Create runner directory
mkdir -p ~/actions-runner
cd ~/actions-runner
```

### 3. Download the Latest Runner

```bash
# For x64
curl -o actions-runner-linux-x64.tar.gz -L \
    https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-linux-x64-2.313.0.tar.gz

# For ARM64
curl -o actions-runner-linux-arm64.tar.gz -L \
    https://github.com/actions/runner/releases/download/v2.313.0/actions-runner-linux-arm64-2.313.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-*.tar.gz
rm ./actions-runner-linux-*.tar.gz
```

### 4. Configure the Runner

```bash
# Generate a registration token from GitHub
# Settings > Actions > Runners > New self-hosted runner

./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN

# Configuration prompts:
# - Runner name (default: hostname)
# - Runner group (default: Default)
# - Labels (default: self-hosted,Linux,X64 or ARM64)
# - Work folder (default: _work)
```

### 5. Test the Runner

```bash
./run.sh
# Press Ctrl+C to stop after verifying it connects
```

### 6. Exit Back to Your User

```bash
exit  # Back to your regular user
```

## Installing Claude Code

### 1. Install Claude Code CLI

```bash
# Install as actions-runner user
sudo su - actions-runner

# Create virtual environment (recommended)
python3 -m venv ~/claude-env
source ~/claude-env/bin/activate

# Install Claude Code
pip install --upgrade pip
pip install claude-code

# Or install from source
# git clone https://github.com/anthropics/claude-code.git
# cd claude-code
# pip install -e .

# Exit venv for now
deactivate
exit
```

### 2. Configure Authentication

```bash
# As actions-runner user
sudo su - actions-runner

# Activate venv
source ~/claude-env/bin/activate

# Authenticate
claude auth login

# Verify
claude auth status

# Store API key for service use
mkdir -p ~/.config/lazarus
chmod 700 ~/.config/lazarus
echo "ANTHROPIC_API_KEY=your_api_key_here" > ~/.config/lazarus/env
chmod 600 ~/.config/lazarus/env

deactivate
exit
```

## Creating a systemd Service

### 1. Install the Service

Use the provided script or create manually:

```bash
# Using the provided script
cd /path/to/lazarus/runner-setup/scripts
sudo ./configure-systemd.sh
```

Or create manually:

```bash
# Create service file
sudo nano /etc/systemd/system/actions-runner.service
```

Add the following content:

```ini
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=actions-runner
WorkingDirectory=/home/actions-runner/actions-runner
ExecStart=/home/actions-runner/actions-runner/run.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=actions-runner

# Environment variables
Environment="PATH=/home/actions-runner/claude-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HOME=/home/actions-runner"
EnvironmentFile=-/home/actions-runner/.config/lazarus/env

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/actions-runner/actions-runner

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable actions-runner

# Start service
sudo systemctl start actions-runner

# Check status
sudo systemctl status actions-runner
```

### 3. Verify Service is Running

```bash
# Check service status
sudo systemctl status actions-runner

# View logs
sudo journalctl -u actions-runner -f

# Check process
ps aux | grep actions-runner

# Use health check script
/path/to/lazarus/runner-setup/scripts/check-runner-health.sh
```

## Service Configuration

### Environment Variables

Edit `/etc/systemd/system/actions-runner.service` to add variables:

```ini
Environment="CUSTOM_VAR=value"
EnvironmentFile=/home/actions-runner/.config/lazarus/env
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart actions-runner
```

### Working Directory

The service runs from `/home/actions-runner/actions-runner` by default. Change with:

```ini
WorkingDirectory=/path/to/runner
```

### Service User

To change the user:

```ini
User=different-user
```

Ensure the user has access to the runner directory.

### Resource Limits

Adjust limits based on your needs:

```ini
# File descriptors
LimitNOFILE=65536

# Number of processes
LimitNPROC=4096

# Memory limit (optional)
MemoryLimit=4G

# CPU quota (optional, 200% = 2 cores)
CPUQuota=200%
```

## Security Hardening

### 1. Service Security Options

The service file includes several security options:

```ini
# Prevent privilege escalation
NoNewPrivileges=true

# Private /tmp directory
PrivateTmp=true

# Read-only system directories
ProtectSystem=strict

# Limited home directory access
ProtectHome=read-only

# Writable paths
ReadWritePaths=/home/actions-runner/actions-runner
```

### 2. File Permissions

```bash
# Secure runner directory
sudo chmod 700 /home/actions-runner/actions-runner

# Secure configuration
sudo chmod 600 /home/actions-runner/.config/lazarus/env

# Secure service file
sudo chmod 644 /etc/systemd/system/actions-runner.service
```

### 3. Firewall Configuration

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow from 192.30.252.0/22 to any port 443 proto tcp
sudo ufw allow from 185.199.108.0/22 to any port 443 proto tcp
sudo ufw enable

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
    source address="192.30.252.0/22" port protocol="tcp" port="443" accept'
sudo firewall-cmd --reload
```

### 4. SELinux Configuration (RHEL/CentOS)

```bash
# Check SELinux status
getenforce

# If enforcing, allow runner to execute
sudo semanage fcontext -a -t bin_t "/home/actions-runner/actions-runner/.*"
sudo restorecon -R /home/actions-runner/actions-runner

# Allow network access
sudo setsebool -P nis_enabled 1
```

### 5. AppArmor Configuration (Ubuntu/Debian)

```bash
# Create AppArmor profile if needed
sudo nano /etc/apparmor.d/actions-runner

# Basic profile
# /home/actions-runner/actions-runner/run.sh {
#     /home/actions-runner/actions-runner/** r,
#     /home/actions-runner/actions-runner/_work/** rw,
# }

# Load profile
sudo apparmor_parser -r /etc/apparmor.d/actions-runner
```

### 6. API Key Security

```bash
# Store API key securely
sudo chmod 600 /home/actions-runner/.config/lazarus/env

# Ensure only actions-runner user can read
sudo chown actions-runner:actions-runner /home/actions-runner/.config/lazarus/env

# Never log API keys
# Ensure they're not in systemd journal
sudo journalctl -u actions-runner | grep -i "api" | grep -i "key"  # Should be empty
```

### 7. Audit Logging

```bash
# Enable audit rules for runner directory
sudo auditctl -w /home/actions-runner/actions-runner -p wa -k actions-runner

# View audit logs
sudo ausearch -k actions-runner
```

### 8. User Isolation

```bash
# Limit sudo access
# DO NOT add actions-runner to sudoers

# Use dedicated group
sudo groupadd github-runners
sudo usermod -g github-runners actions-runner

# Restrict access to runner files
sudo chmod 700 /home/actions-runner
```

## Monitoring and Logs

### Viewing Logs

```bash
# Real-time logs
sudo journalctl -u actions-runner -f

# Recent logs
sudo journalctl -u actions-runner -n 100

# Logs since boot
sudo journalctl -u actions-runner -b

# Logs from specific time
sudo journalctl -u actions-runner --since "1 hour ago"

# Export logs
sudo journalctl -u actions-runner > runner-logs.txt
```

### Log Rotation

systemd handles log rotation automatically, but you can configure it:

```bash
# Edit journald config
sudo nano /etc/systemd/journald.conf

# Set retention
SystemMaxUse=1G
SystemMaxFileSize=100M
MaxRetentionSec=1month

# Restart journald
sudo systemctl restart systemd-journald
```

### Monitoring Service Health

```bash
# Service status
sudo systemctl status actions-runner

# Service failures
sudo systemctl list-units --failed

# Resource usage
systemctl status actions-runner | grep -A 5 "Memory\|CPU"

# Detailed resource usage
sudo systemd-cgtop
```

### Performance Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs  # Ubuntu/Debian
sudo dnf install htop iotop nethogs  # RHEL/CentOS

# Monitor CPU/Memory
htop

# Monitor I/O
sudo iotop

# Monitor network
sudo nethogs

# Check disk usage
df -h /home/actions-runner/actions-runner/_work
```

### Setting Up Alerts

Create a monitoring script:

```bash
sudo nano /usr/local/bin/monitor-runner.sh
```

```bash
#!/bin/bash
# Monitor runner and send alerts

if ! systemctl is-active --quiet actions-runner; then
    # Send alert (email, Slack, etc.)
    echo "Runner is down!" | mail -s "Runner Alert" admin@example.com
fi

# Check disk space
USAGE=$(df -h /home/actions-runner | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$USAGE" -gt 80 ]; then
    echo "Disk usage is ${USAGE}%" | mail -s "Disk Alert" admin@example.com
fi
```

Add to crontab:
```bash
sudo crontab -e
# Add: */5 * * * * /usr/local/bin/monitor-runner.sh
```

### Metrics Collection

For advanced monitoring, integrate with Prometheus:

```bash
# Install node_exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz
sudo mv node_exporter-*/node_exporter /usr/local/bin/
sudo useradd -rs /bin/false node_exporter

# Create systemd service
sudo nano /etc/systemd/system/node_exporter.service
```

## Troubleshooting

### Service Won't Start

**Problem**: Service fails to start

**Solution**:
```bash
# Check service status
sudo systemctl status actions-runner

# View logs
sudo journalctl -u actions-runner -n 50

# Check configuration
sudo systemctl cat actions-runner

# Verify user exists
id actions-runner

# Check file permissions
ls -la /home/actions-runner/actions-runner/

# Test manually
sudo su - actions-runner
cd ~/actions-runner
./run.sh
```

### Permission Denied Errors

**Problem**: Runner can't access files or execute scripts

**Solution**:
```bash
# Fix ownership
sudo chown -R actions-runner:actions-runner /home/actions-runner/actions-runner

# Fix permissions
sudo chmod +x /home/actions-runner/actions-runner/*.sh
sudo chmod 700 /home/actions-runner/actions-runner

# Check SELinux (if applicable)
sudo getenforce
sudo ausearch -m avc -ts recent
```

### Runner Disconnects Frequently

**Problem**: Runner shows as offline

**Solution**:
```bash
# Check network connectivity
ping github.com

# Check firewall
sudo iptables -L -n
sudo firewall-cmd --list-all

# Increase restart delay
sudo nano /etc/systemd/system/actions-runner.service
# Change: RestartSec=30

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart actions-runner
```

### High Memory Usage

**Problem**: Runner consuming too much memory

**Solution**:
```bash
# Check memory usage
free -h
sudo systemctl status actions-runner

# Set memory limit
sudo systemctl edit actions-runner
# Add:
# [Service]
# MemoryLimit=4G

# Reload
sudo systemctl daemon-reload
sudo systemctl restart actions-runner
```

### Disk Space Issues

**Problem**: Disk full

**Solution**:
```bash
# Check disk usage
df -h
du -sh /home/actions-runner/actions-runner/_work/*

# Clean old workflows
find /home/actions-runner/actions-runner/_work -type d -mtime +7 -exec rm -rf {} +

# Clean logs
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=500M

# Set up automatic cleanup
sudo crontab -e
# Add: 0 2 * * * find /home/actions-runner/actions-runner/_work -type d -mtime +7 -delete
```

### Claude Code Not Working

**Problem**: Claude Code authentication fails

**Solution**:
```bash
# Check API key
sudo su - actions-runner
source ~/claude-env/bin/activate
echo $ANTHROPIC_API_KEY

# Re-authenticate
claude auth logout
claude auth login

# Verify environment file
cat ~/.config/lazarus/env

# Ensure service loads environment
sudo systemctl cat actions-runner | grep EnvironmentFile

# Restart service
exit
sudo systemctl restart actions-runner
```

### SELinux Blocking Execution

**Problem**: SELinux denies runner operations

**Solution**:
```bash
# Check for denials
sudo ausearch -m avc -ts recent

# Allow execution
sudo semanage fcontext -a -t bin_t "/home/actions-runner/actions-runner/(.*)?/bin/.*"
sudo restorecon -R /home/actions-runner/actions-runner

# Generate policy from denials
sudo audit2allow -a -M actions-runner
sudo semodule -i actions-runner.pp

# Verify
sudo semodule -l | grep actions-runner
```

### Service Crashes on Boot

**Problem**: Service fails after system reboot

**Solution**:
```bash
# Check dependency order
sudo systemctl cat actions-runner

# Add network dependency
sudo systemctl edit actions-runner
# Add:
# [Unit]
# After=network-online.target
# Wants=network-online.target

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable actions-runner
```

## Maintenance Tasks

### Daily

- Monitor service status
- Check disk space usage
- Review logs for errors

### Weekly

- Update runner binary
- Review failed workflows
- Clean old workflow data
- Verify authentication

### Monthly

- Update system packages
- Review security logs
- Rotate API keys (if required)
- Test backup/restore procedures

### Quarterly

- Security audit
- Performance review
- Capacity planning
- Update documentation

## Useful Commands

```bash
# Service management
sudo systemctl start actions-runner
sudo systemctl stop actions-runner
sudo systemctl restart actions-runner
sudo systemctl status actions-runner
sudo systemctl enable actions-runner
sudo systemctl disable actions-runner

# Logs
sudo journalctl -u actions-runner -f
sudo journalctl -u actions-runner -n 100
sudo journalctl -u actions-runner --since "1 hour ago"

# Health check
/path/to/lazarus/runner-setup/scripts/check-runner-health.sh

# Update
/path/to/lazarus/runner-setup/scripts/update-runner.sh

# Configuration
sudo systemctl edit actions-runner
sudo systemctl daemon-reload
sudo systemctl cat actions-runner
```

## Additional Resources

- [GitHub Actions Self-Hosted Runner Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [systemd Documentation](https://www.freedesktop.org/software/systemd/man/)
- [Lazarus GitHub Repository](https://github.com/YOUR_ORG/lazarus)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Linux Security Hardening Guide](https://www.cisecurity.org/cis-benchmarks/)

## Support

For issues not covered in this guide:

1. Check [GitHub Actions Community Forum](https://github.community/c/github-actions)
2. Review systemd logs: `sudo journalctl -u actions-runner`
3. Open an issue in the Lazarus repository
4. Contact your system administrator
