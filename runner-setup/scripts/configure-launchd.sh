#!/usr/bin/env bash
#
# configure-launchd.sh
# macOS LaunchAgent configuration for GitHub Actions runner
#
# This script creates and configures a LaunchAgent to run the
# GitHub Actions runner as a background service on macOS.
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
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner}"
PLIST_NAME="com.github.actions.runner"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
ENV_FILE="$HOME/.config/lazarus/env"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "This script should not be run as root"
    error "Run as the user who will run the runner"
    exit 1
fi

# Validate runner directory
validate_runner() {
    info "Validating runner installation..."

    if [ ! -d "$RUNNER_DIR" ]; then
        error "Runner directory not found: $RUNNER_DIR"
        echo ""
        echo "Please run install-runner.sh first or set RUNNER_DIR environment variable"
        exit 1
    fi

    if [ ! -f "$RUNNER_DIR/run.sh" ]; then
        error "Runner executable not found: $RUNNER_DIR/run.sh"
        exit 1
    fi

    if [ ! -x "$RUNNER_DIR/run.sh" ]; then
        error "Runner executable is not executable"
        info "Fixing permissions..."
        chmod +x "$RUNNER_DIR/run.sh"
    fi

    success "Runner installation validated"
}

# Get environment variables
collect_environment() {
    info "Collecting environment variables..."

    # Start with basic PATH
    ENV_PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    # Add Homebrew paths
    if [ -d "/opt/homebrew/bin" ]; then
        ENV_PATH="/opt/homebrew/bin:$ENV_PATH"
        info "Added Homebrew ARM64 to PATH"
    fi

    if [ -d "/usr/local/bin" ]; then
        ENV_PATH="/usr/local/bin:$ENV_PATH"
        info "Added Homebrew x64 to PATH"
    fi

    # Check for Claude Code
    if command -v claude &> /dev/null; then
        CLAUDE_PATH=$(dirname "$(command -v claude)")
        if [[ ! "$ENV_PATH" =~ "$CLAUDE_PATH" ]]; then
            ENV_PATH="$CLAUDE_PATH:$ENV_PATH"
            info "Added Claude Code to PATH: $CLAUDE_PATH"
        fi
    else
        warning "Claude Code not found in PATH"
        warning "Install with: pip install claude-code"
    fi

    # Check for Python venv
    if [ -d "$HOME/claude-env/bin" ]; then
        ENV_PATH="$HOME/claude-env/bin:$ENV_PATH"
        info "Added Python virtual environment to PATH"
    fi

    # Check for API key file
    if [ -f "$ENV_FILE" ]; then
        info "Found environment file: $ENV_FILE"
        USE_ENV_FILE=true
    else
        warning "Environment file not found: $ENV_FILE"
        warning "Create it with: echo 'ANTHROPIC_API_KEY=your_key' > $ENV_FILE"
        USE_ENV_FILE=false
    fi

    success "Environment collected"
}

# Create LaunchAgent plist
create_plist() {
    info "Creating LaunchAgent configuration..."

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"

    # Unload existing service if running
    if launchctl list | grep -q "$PLIST_NAME"; then
        info "Unloading existing service..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
    fi

    # Create plist file
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>$RUNNER_DIR/run.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>$RUNNER_DIR/runner.log</string>

    <key>StandardErrorPath</key>
    <string>$RUNNER_DIR/runner-error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$ENV_PATH</string>
        <key>HOME</key>
        <string>$HOME</string>
EOF

    # Add environment variables from file if it exists
    if [ "$USE_ENV_FILE" = true ]; then
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue

            # Remove quotes from value if present
            value="${value%\"}"
            value="${value#\"}"

            cat >> "$PLIST_PATH" << EOF
        <key>$key</key>
        <string>$value</string>
EOF
        done < "$ENV_FILE"
    fi

    cat >> "$PLIST_PATH" << EOF
    </dict>

    <key>WorkingDirectory</key>
    <string>$RUNNER_DIR</string>

    <key>SessionCreate</key>
    <true/>

    <key>ProcessType</key>
    <string>Interactive</string>

    <key>Nice</key>
    <integer>0</integer>
</dict>
</plist>
EOF

    # Set permissions
    chmod 644 "$PLIST_PATH"

    success "LaunchAgent configuration created: $PLIST_PATH"
}

# Validate plist syntax
validate_plist() {
    info "Validating plist syntax..."

    if plutil -lint "$PLIST_PATH" > /dev/null 2>&1; then
        success "Plist syntax is valid"
    else
        error "Plist syntax validation failed"
        plutil -lint "$PLIST_PATH"
        exit 1
    fi
}

# Load and start service
start_service() {
    info "Loading LaunchAgent..."

    if launchctl load "$PLIST_PATH"; then
        success "LaunchAgent loaded"
    else
        error "Failed to load LaunchAgent"
        exit 1
    fi

    sleep 2

    info "Starting service..."

    if launchctl start "$PLIST_NAME"; then
        success "Service started"
    else
        warning "Service may have already started automatically"
    fi

    sleep 2
}

# Check service status
check_status() {
    info "Checking service status..."

    if launchctl list | grep -q "$PLIST_NAME"; then
        success "Service is loaded"

        # Get PID
        if PID=$(launchctl list | grep "$PLIST_NAME" | awk '{print $1}'); then
            if [ "$PID" != "-" ]; then
                success "Service is running (PID: $PID)"
            else
                warning "Service is loaded but not running"
                warning "Check logs at: $RUNNER_DIR/runner-error.log"
            fi
        fi
    else
        error "Service is not loaded"
        exit 1
    fi

    # Check runner process
    if ps aux | grep -v grep | grep -q "$RUNNER_DIR/run.sh"; then
        success "Runner process is active"
    else
        warning "Runner process not found"
    fi

    # Check logs
    if [ -f "$RUNNER_DIR/runner.log" ]; then
        info "Recent log entries:"
        echo ""
        tail -n 10 "$RUNNER_DIR/runner.log"
        echo ""
    fi
}

# Configure auto-start
configure_autostart() {
    echo ""
    info "Auto-start Configuration"
    echo ""
    echo "The LaunchAgent is configured to start automatically on login."
    echo "This means it will start when you log in to your user account."
    echo ""

    read -p "Do you want to enable auto-start on boot (system-wide)? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        warning "System-wide auto-start requires creating a LaunchDaemon (requires sudo)"
        warning "This is not recommended for security reasons"
        echo ""

        read -p "Continue with LaunchDaemon creation? [y/N] " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_launch_daemon
        fi
    fi

    success "Auto-start configuration complete"
}

# Create LaunchDaemon (system-wide)
create_launch_daemon() {
    DAEMON_NAME="com.github.actions.runner"
    DAEMON_PATH="/Library/LaunchDaemons/$DAEMON_NAME.plist"

    info "Creating LaunchDaemon..."

    # Unload LaunchAgent first
    launchctl unload "$PLIST_PATH" 2>/dev/null || true

    sudo tee "$DAEMON_PATH" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$DAEMON_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>$RUNNER_DIR/run.sh</string>
    </array>

    <key>UserName</key>
    <string>$USER</string>

    <key>GroupName</key>
    <string>staff</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$RUNNER_DIR/runner.log</string>

    <key>StandardErrorPath</key>
    <string>$RUNNER_DIR/runner-error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$ENV_PATH</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>$RUNNER_DIR</string>
</dict>
</plist>
EOF

    sudo chmod 644 "$DAEMON_PATH"
    sudo chown root:wheel "$DAEMON_PATH"

    # Load daemon
    sudo launchctl load "$DAEMON_PATH"

    success "LaunchDaemon created and loaded"
    info "The runner will now start on system boot"
}

# Print summary
print_summary() {
    echo ""
    echo "========================================"
    success "LaunchAgent Configuration Complete!"
    echo "========================================"
    echo ""
    echo "Service Details:"
    echo "  - Name: $PLIST_NAME"
    echo "  - Config: $PLIST_PATH"
    echo "  - Runner: $RUNNER_DIR"
    echo ""
    echo "Useful Commands:"
    echo "  Start:     launchctl start $PLIST_NAME"
    echo "  Stop:      launchctl stop $PLIST_NAME"
    echo "  Restart:   launchctl stop $PLIST_NAME && launchctl start $PLIST_NAME"
    echo "  Unload:    launchctl unload $PLIST_PATH"
    echo "  Load:      launchctl load $PLIST_PATH"
    echo "  Status:    launchctl list | grep $PLIST_NAME"
    echo ""
    echo "Logs:"
    echo "  Output:    tail -f $RUNNER_DIR/runner.log"
    echo "  Errors:    tail -f $RUNNER_DIR/runner-error.log"
    echo "  System:    log show --predicate 'processImagePath contains \"actions-runner\"' --last 1h"
    echo ""
    echo "Next Steps:"
    echo "  1. Verify runner appears in GitHub"
    echo "  2. Test with a workflow"
    echo "  3. Monitor logs for errors"
    echo ""
}

# Main function
main() {
    echo ""
    echo "========================================"
    echo "macOS LaunchAgent Configuration"
    echo "========================================"
    echo ""

    validate_runner
    collect_environment
    create_plist
    validate_plist
    start_service
    check_status
    configure_autostart
    print_summary
}

# Run main function
main "$@"
