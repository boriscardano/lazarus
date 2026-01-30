#!/usr/bin/env bash
#
# configure-systemd.sh
# Linux systemd service configuration for GitHub Actions runner
#
# This script creates and configures a systemd service to run the
# GitHub Actions runner as a background service on Linux.
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Output functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SERVICE_NAME="actions-runner"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
RUNNER_USER="${RUNNER_USER:-actions-runner}"
RUNNER_DIR="/home/$RUNNER_USER/actions-runner"
ENV_FILE="/home/$RUNNER_USER/.config/lazarus/env"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

# Validate runner installation
validate_runner() {
    info "Validating runner installation..."

    # Check if user exists
    if ! id -u "$RUNNER_USER" &> /dev/null; then
        error "User '$RUNNER_USER' does not exist"
        echo ""
        read -p "Create user '$RUNNER_USER' now? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            info "Creating user '$RUNNER_USER'..."
            useradd -m -s /bin/bash "$RUNNER_USER"
            success "User created"
        else
            exit 1
        fi
    else
        success "User '$RUNNER_USER' exists"
    fi

    # Check runner directory
    if [ ! -d "$RUNNER_DIR" ]; then
        error "Runner directory not found: $RUNNER_DIR"
        echo ""
        echo "Please run install-runner.sh first"
        exit 1
    fi

    if [ ! -f "$RUNNER_DIR/run.sh" ]; then
        error "Runner executable not found: $RUNNER_DIR/run.sh"
        exit 1
    fi

    if [ ! -x "$RUNNER_DIR/run.sh" ]; then
        info "Fixing executable permissions..."
        chmod +x "$RUNNER_DIR/run.sh"
    fi

    # Ensure proper ownership
    chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

    success "Runner installation validated"
}

# Collect environment configuration
collect_environment() {
    info "Collecting environment configuration..."

    # Build PATH
    ENV_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

    # Check for Claude Code
    CLAUDE_PATH=""
    if [ -d "/home/$RUNNER_USER/claude-env/bin" ]; then
        CLAUDE_PATH="/home/$RUNNER_USER/claude-env/bin"
        ENV_PATH="$CLAUDE_PATH:$ENV_PATH"
        info "Found Claude virtual environment"
    elif command -v claude &> /dev/null; then
        CLAUDE_PATH=$(dirname "$(command -v claude)")
        ENV_PATH="$CLAUDE_PATH:$ENV_PATH"
        info "Found Claude Code in system PATH"
    else
        warning "Claude Code not found"
        warning "Install with: pip install claude-code"
    fi

    # Check for environment file
    if [ -f "$ENV_FILE" ]; then
        info "Found environment file: $ENV_FILE"
        USE_ENV_FILE=true

        # Ensure proper permissions
        chmod 600 "$ENV_FILE"
        chown "$RUNNER_USER:$RUNNER_USER" "$ENV_FILE"
    else
        warning "Environment file not found: $ENV_FILE"
        warning "Create it with API key: echo 'ANTHROPIC_API_KEY=your_key' > $ENV_FILE"
        USE_ENV_FILE=false
    fi

    success "Environment collected"
}

# Get resource limits
configure_limits() {
    info "Configuring resource limits..."

    # Default values
    MEMORY_LIMIT=""
    CPU_QUOTA=""
    FILE_LIMIT="65536"
    PROC_LIMIT="4096"

    echo ""
    read -p "Set memory limit? (e.g., 4G, 8G) [leave empty for no limit]: " MEMORY_INPUT
    if [ -n "$MEMORY_INPUT" ]; then
        MEMORY_LIMIT="$MEMORY_INPUT"
        info "Memory limit set to: $MEMORY_LIMIT"
    fi

    read -p "Set CPU quota? (e.g., 200% for 2 cores) [leave empty for no limit]: " CPU_INPUT
    if [ -n "$CPU_INPUT" ]; then
        CPU_QUOTA="$CPU_INPUT"
        info "CPU quota set to: $CPU_QUOTA"
    fi

    success "Resource limits configured"
}

# Create systemd service file
create_service() {
    info "Creating systemd service file..."

    # Stop existing service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "Stopping existing service..."
        systemctl stop "$SERVICE_NAME"
    fi

    # Disable existing service if enabled
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        info "Disabling existing service..."
        systemctl disable "$SERVICE_NAME"
    fi

    # Create service file
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GitHub Actions Runner
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUNNER_USER
WorkingDirectory=$RUNNER_DIR
ExecStart=$RUNNER_DIR/run.sh

# Restart configuration
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Environment
Environment="PATH=$ENV_PATH"
Environment="HOME=/home/$RUNNER_USER"
EOF

    # Add environment file if it exists
    if [ "$USE_ENV_FILE" = true ]; then
        echo "EnvironmentFile=-$ENV_FILE" >> "$SERVICE_FILE"
    fi

    # Add resource limits
    cat >> "$SERVICE_FILE" << EOF

# Resource limits
LimitNOFILE=$FILE_LIMIT
LimitNPROC=$PROC_LIMIT
EOF

    if [ -n "$MEMORY_LIMIT" ]; then
        echo "MemoryLimit=$MEMORY_LIMIT" >> "$SERVICE_FILE"
    fi

    if [ -n "$CPU_QUOTA" ]; then
        echo "CPUQuota=$CPU_QUOTA" >> "$SERVICE_FILE"
    fi

    # Add security hardening
    cat >> "$SERVICE_FILE" << EOF

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$RUNNER_DIR

# Allow creating files in work directory
ReadWritePaths=$RUNNER_DIR/_work

[Install]
WantedBy=multi-user.target
EOF

    # Set permissions
    chmod 644 "$SERVICE_FILE"

    success "Service file created: $SERVICE_FILE"
}

# Configure SELinux if needed
configure_selinux() {
    if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
        info "Configuring SELinux..."

        # Set context for runner directory
        if command -v semanage &> /dev/null; then
            semanage fcontext -a -t bin_t "$RUNNER_DIR(/.*)?" 2>/dev/null || true
            restorecon -R "$RUNNER_DIR"
            success "SELinux configured"
        else
            warning "semanage not found, skipping SELinux configuration"
            warning "Install with: yum install policycoreutils-python-utils"
        fi
    fi
}

# Enable and start service
start_service() {
    info "Reloading systemd daemon..."
    systemctl daemon-reload

    echo ""
    read -p "Enable service to start on boot? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        info "Enabling service..."
        systemctl enable "$SERVICE_NAME"
        success "Service enabled"
    fi

    echo ""
    read -p "Start service now? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        info "Starting service..."
        systemctl start "$SERVICE_NAME"
        sleep 2
        success "Service started"
    fi
}

# Check service status
check_status() {
    info "Checking service status..."
    echo ""

    systemctl status "$SERVICE_NAME" --no-pager || true

    echo ""

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Service is running"
    else
        warning "Service is not running"
        echo ""
        info "Check logs with: journalctl -u $SERVICE_NAME -n 50"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        success "Service is enabled (will start on boot)"
    else
        info "Service is not enabled (will not start on boot)"
    fi
}

# Show recent logs
show_logs() {
    echo ""
    read -p "Show recent logs? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        info "Recent log entries:"
        echo ""
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
        echo ""
    fi
}

# Configure log rotation
configure_logging() {
    echo ""
    read -p "Configure log rotation? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        info "Configuring journald..."

        # Create journald drop-in directory
        mkdir -p /etc/systemd/journald.conf.d

        cat > /etc/systemd/journald.conf.d/actions-runner.conf << EOF
[Journal]
# Limit journal size for actions-runner
SystemMaxUse=1G
SystemMaxFileSize=100M
MaxRetentionSec=1month
EOF

        info "Restarting journald..."
        systemctl restart systemd-journald

        success "Log rotation configured"
    fi
}

# Configure firewall
configure_firewall() {
    echo ""
    read -p "Configure firewall rules? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Detect firewall
        if command -v ufw &> /dev/null; then
            info "Configuring ufw..."
            ufw allow from 192.30.252.0/22 to any port 443 proto tcp comment 'GitHub Actions'
            ufw allow from 185.199.108.0/22 to any port 443 proto tcp comment 'GitHub Actions'
            success "ufw configured"
        elif command -v firewall-cmd &> /dev/null; then
            info "Configuring firewalld..."
            firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.30.252.0/22" port port="443" protocol="tcp" accept'
            firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="185.199.108.0/22" port port="443" protocol="tcp" accept'
            firewall-cmd --reload
            success "firewalld configured"
        else
            warning "No supported firewall found (ufw or firewalld)"
        fi
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "========================================"
    success "systemd Service Configuration Complete!"
    echo "========================================"
    echo ""
    echo "Service Details:"
    echo "  - Name: $SERVICE_NAME"
    echo "  - Config: $SERVICE_FILE"
    echo "  - User: $RUNNER_USER"
    echo "  - Runner: $RUNNER_DIR"
    echo ""
    echo "Useful Commands:"
    echo "  Start:     sudo systemctl start $SERVICE_NAME"
    echo "  Stop:      sudo systemctl stop $SERVICE_NAME"
    echo "  Restart:   sudo systemctl restart $SERVICE_NAME"
    echo "  Status:    sudo systemctl status $SERVICE_NAME"
    echo "  Enable:    sudo systemctl enable $SERVICE_NAME"
    echo "  Disable:   sudo systemctl disable $SERVICE_NAME"
    echo ""
    echo "Logs:"
    echo "  Live:      sudo journalctl -u $SERVICE_NAME -f"
    echo "  Recent:    sudo journalctl -u $SERVICE_NAME -n 100"
    echo "  Since:     sudo journalctl -u $SERVICE_NAME --since \"1 hour ago\""
    echo "  Export:    sudo journalctl -u $SERVICE_NAME > logs.txt"
    echo ""
    echo "Troubleshooting:"
    echo "  Config:    sudo systemctl cat $SERVICE_NAME"
    echo "  Reload:    sudo systemctl daemon-reload"
    echo "  Failed:    sudo systemctl list-units --failed"
    echo ""
    echo "Next Steps:"
    echo "  1. Verify runner appears in GitHub"
    echo "  2. Test with a workflow"
    echo "  3. Monitor logs for errors"
    echo "  4. Set up monitoring/alerting"
    echo ""
}

# Main function
main() {
    echo ""
    echo "========================================"
    echo "Linux systemd Service Configuration"
    echo "========================================"
    echo ""

    validate_runner
    collect_environment
    configure_limits
    create_service
    configure_selinux
    start_service
    check_status
    show_logs
    configure_logging
    configure_firewall
    print_summary
}

# Run main function
main "$@"
