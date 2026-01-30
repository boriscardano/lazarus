#!/usr/bin/env bash
#
# check-runner-health.sh
# Health check script for GitHub Actions runner
#
# This script verifies that the runner is functioning correctly,
# including runner process, Claude Code authentication, gh CLI,
# disk space, and other critical components.
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Status symbols
CHECK="✓"
CROSS="✗"
WARN="⚠"

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0
TOTAL_CHECKS=0

# Output functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}${CHECK}${NC} $1"; ((CHECKS_PASSED++)); ((TOTAL_CHECKS++)); }
failure() { echo -e "${RED}${CROSS}${NC} $1"; ((CHECKS_FAILED++)); ((TOTAL_CHECKS++)); }
warning() { echo -e "${YELLOW}${WARN}${NC} $1"; ((CHECKS_WARNING++)); ((TOTAL_CHECKS++)); }
header() { echo -e "\n${BOLD}$1${NC}"; }

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        SERVICE_NAME="com.github.actions.runner"
    else
        OS_TYPE="linux"
        SERVICE_NAME="actions-runner"
    fi
}

# Check runner directory
check_runner_directory() {
    header "Runner Installation"

    # Detect runner directory
    if [[ "$OS_TYPE" == "macos" ]]; then
        RUNNER_DIR="$HOME/actions-runner"
    else
        if [ -d "/home/actions-runner/actions-runner" ]; then
            RUNNER_DIR="/home/actions-runner/actions-runner"
        else
            RUNNER_DIR="$HOME/actions-runner"
        fi
    fi

    if [ -d "$RUNNER_DIR" ]; then
        success "Runner directory exists: $RUNNER_DIR"
    else
        failure "Runner directory not found"
        return
    fi

    if [ -f "$RUNNER_DIR/run.sh" ]; then
        success "Runner executable found"
    else
        failure "Runner executable not found"
    fi

    if [ -f "$RUNNER_DIR/.runner" ]; then
        success "Runner configuration found"

        # Parse runner config
        if command -v jq &> /dev/null && [ -f "$RUNNER_DIR/.runner" ]; then
            RUNNER_NAME=$(jq -r '.agentName' "$RUNNER_DIR/.runner" 2>/dev/null || echo "unknown")
            info "  Runner name: $RUNNER_NAME"
        fi
    else
        failure "Runner not configured"
    fi
}

# Check runner process
check_runner_process() {
    header "Runner Process"

    if pgrep -f "actions-runner.*run.sh" > /dev/null; then
        PID=$(pgrep -f "actions-runner.*run.sh" | head -n 1)
        success "Runner process is running (PID: $PID)"

        # Check process age
        if [[ "$OS_TYPE" == "macos" ]]; then
            START_TIME=$(ps -p "$PID" -o lstart= 2>/dev/null || echo "unknown")
        else
            START_TIME=$(ps -p "$PID" -o lstart= 2>/dev/null || echo "unknown")
        fi
        info "  Started: $START_TIME"

        # Check CPU and memory usage
        if [[ "$OS_TYPE" == "macos" ]]; then
            CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null | xargs)
            MEM=$(ps -p "$PID" -o %mem= 2>/dev/null | xargs)
        else
            CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null | xargs)
            MEM=$(ps -p "$PID" -o %mem= 2>/dev/null | xargs)
        fi

        if [ -n "$CPU" ] && [ -n "$MEM" ]; then
            info "  CPU: ${CPU}%  Memory: ${MEM}%"
        fi
    else
        failure "Runner process not running"
    fi
}

# Check service status
check_service() {
    header "Service Status"

    if [[ "$OS_TYPE" == "macos" ]]; then
        # Check LaunchAgent
        if launchctl list | grep -q "$SERVICE_NAME"; then
            success "LaunchAgent is loaded"

            STATUS=$(launchctl list | grep "$SERVICE_NAME")
            PID=$(echo "$STATUS" | awk '{print $1}')

            if [ "$PID" != "-" ]; then
                success "Service is running"
            else
                failure "Service is loaded but not running"
            fi
        else
            warning "LaunchAgent not loaded (runner may be running manually)"
        fi
    else
        # Check systemd service
        if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            success "systemd service is active"
        else
            failure "systemd service is not active"
        fi

        if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
            success "systemd service is enabled"
        else
            warning "systemd service is not enabled (won't start on boot)"
        fi
    fi
}

# Check Claude Code
check_claude_code() {
    header "Claude Code"

    if command -v claude &> /dev/null; then
        success "Claude Code CLI is installed"

        VERSION=$(claude --version 2>/dev/null || echo "unknown")
        info "  Version: $VERSION"

        # Check authentication
        if claude auth status &> /dev/null; then
            success "Claude Code is authenticated"
        else
            failure "Claude Code is not authenticated"
            info "  Run: claude auth login"
        fi
    else
        failure "Claude Code CLI not found"
        info "  Install with: pip install claude-code"
    fi
}

# Check GitHub CLI
check_gh_cli() {
    header "GitHub CLI"

    if command -v gh &> /dev/null; then
        success "GitHub CLI is installed"

        VERSION=$(gh --version | head -n 1)
        info "  Version: $VERSION"

        # Check authentication
        if gh auth status &> /dev/null; then
            success "GitHub CLI is authenticated"

            # Get authenticated user
            USER=$(gh api user --jq .login 2>/dev/null || echo "unknown")
            info "  User: $USER"
        else
            warning "GitHub CLI is not authenticated"
            info "  Run: gh auth login"
        fi
    else
        warning "GitHub CLI not found (optional)"
        info "  Install from: https://cli.github.com/"
    fi
}

# Check disk space
check_disk_space() {
    header "Disk Space"

    # Get disk usage for runner directory
    if [ -d "$RUNNER_DIR" ]; then
        if [[ "$OS_TYPE" == "macos" ]]; then
            DISK_USAGE=$(df -h "$RUNNER_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
            DISK_AVAIL=$(df -h "$RUNNER_DIR" | awk 'NR==2 {print $4}')
        else
            DISK_USAGE=$(df -h "$RUNNER_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
            DISK_AVAIL=$(df -h "$RUNNER_DIR" | awk 'NR==2 {print $4}')
        fi

        if [ "$DISK_USAGE" -lt 70 ]; then
            success "Disk usage is healthy (${DISK_USAGE}% used, $DISK_AVAIL available)"
        elif [ "$DISK_USAGE" -lt 85 ]; then
            warning "Disk usage is moderate (${DISK_USAGE}% used, $DISK_AVAIL available)"
        else
            failure "Disk usage is critical (${DISK_USAGE}% used, $DISK_AVAIL available)"
            info "  Consider cleaning old workflow data"
        fi

        # Check work directory size
        if [ -d "$RUNNER_DIR/_work" ]; then
            WORK_SIZE=$(du -sh "$RUNNER_DIR/_work" 2>/dev/null | awk '{print $1}')
            info "  Work directory size: $WORK_SIZE"
        fi
    fi
}

# Check network connectivity
check_network() {
    header "Network Connectivity"

    # Check GitHub connectivity
    if ping -c 1 github.com &> /dev/null; then
        success "GitHub is reachable"
    else
        failure "Cannot reach GitHub"
    fi

    # Check API connectivity
    if curl -s --max-time 5 https://api.github.com/zen &> /dev/null; then
        success "GitHub API is accessible"
    else
        failure "Cannot access GitHub API"
    fi

    # Check Anthropic API
    if curl -s --max-time 5 https://api.anthropic.com &> /dev/null; then
        success "Anthropic API is accessible"
    else
        warning "Cannot access Anthropic API (may be blocked)"
    fi
}

# Check logs for errors
check_logs() {
    header "Recent Logs"

    ERROR_COUNT=0

    if [[ "$OS_TYPE" == "macos" ]]; then
        # Check runner logs
        if [ -f "$RUNNER_DIR/runner.log" ]; then
            ERROR_COUNT=$(grep -i "error" "$RUNNER_DIR/runner.log" 2>/dev/null | tail -n 10 | wc -l | xargs)

            if [ "$ERROR_COUNT" -eq 0 ]; then
                success "No recent errors in runner logs"
            else
                warning "Found $ERROR_COUNT recent error(s) in logs"
                info "  Check: tail -f $RUNNER_DIR/runner.log"
            fi
        fi

        # Check error log
        if [ -f "$RUNNER_DIR/runner-error.log" ] && [ -s "$RUNNER_DIR/runner-error.log" ]; then
            warning "Error log contains data"
            info "  Check: tail -f $RUNNER_DIR/runner-error.log"
        fi
    else
        # Check journald logs
        if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            ERROR_COUNT=$(journalctl -u "$SERVICE_NAME" -n 100 --no-pager 2>/dev/null | grep -i "error" | wc -l | xargs)

            if [ "$ERROR_COUNT" -eq 0 ]; then
                success "No recent errors in service logs"
            else
                warning "Found $ERROR_COUNT recent error(s) in logs"
                info "  Check: sudo journalctl -u $SERVICE_NAME -f"
            fi
        fi
    fi
}

# Check environment configuration
check_environment() {
    header "Environment Configuration"

    # Check for environment file
    ENV_FILE=""
    if [[ "$OS_TYPE" == "macos" ]]; then
        ENV_FILE="$HOME/.config/lazarus/env"
    else
        if [ -f "/home/actions-runner/.config/lazarus/env" ]; then
            ENV_FILE="/home/actions-runner/.config/lazarus/env"
        else
            ENV_FILE="$HOME/.config/lazarus/env"
        fi
    fi

    if [ -f "$ENV_FILE" ]; then
        success "Environment file exists: $ENV_FILE"

        # Check permissions
        PERMS=$(stat -f "%Lp" "$ENV_FILE" 2>/dev/null || stat -c "%a" "$ENV_FILE" 2>/dev/null)
        if [ "$PERMS" = "600" ]; then
            success "Environment file has correct permissions (600)"
        else
            warning "Environment file has incorrect permissions ($PERMS)"
            info "  Run: chmod 600 $ENV_FILE"
        fi

        # Check for API key (without exposing it)
        if grep -q "ANTHROPIC_API_KEY=" "$ENV_FILE" 2>/dev/null; then
            success "API key configured in environment file"
        else
            warning "API key not found in environment file"
        fi
    else
        warning "Environment file not found"
        info "  Create: echo 'ANTHROPIC_API_KEY=your_key' > $ENV_FILE"
    fi
}

# Check Python environment
check_python() {
    header "Python Environment"

    if command -v python3 &> /dev/null; then
        success "Python 3 is installed"

        VERSION=$(python3 --version)
        info "  Version: $VERSION"

        # Check for virtual environment
        VENV_DIR=""
        if [[ "$OS_TYPE" == "macos" ]]; then
            VENV_DIR="$HOME/claude-env"
        else
            VENV_DIR="/home/actions-runner/claude-env"
        fi

        if [ -d "$VENV_DIR" ]; then
            success "Virtual environment exists: $VENV_DIR"
        else
            warning "Virtual environment not found (optional)"
        fi

        # Check pip
        if command -v pip3 &> /dev/null; then
            success "pip is installed"
        else
            warning "pip not found"
        fi
    else
        failure "Python 3 not installed"
    fi
}

# Generate health score
calculate_health_score() {
    if [ "$TOTAL_CHECKS" -eq 0 ]; then
        return
    fi

    HEALTH_SCORE=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))

    header "Health Summary"

    echo ""
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "  ${GREEN}Passed:${NC}   $CHECKS_PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $CHECKS_WARNING"
    echo -e "  ${RED}Failed:${NC}   $CHECKS_FAILED"
    echo ""

    if [ "$HEALTH_SCORE" -ge 90 ]; then
        echo -e "Health Score: ${GREEN}${HEALTH_SCORE}%${NC} - Excellent"
    elif [ "$HEALTH_SCORE" -ge 70 ]; then
        echo -e "Health Score: ${YELLOW}${HEALTH_SCORE}%${NC} - Good"
    elif [ "$HEALTH_SCORE" -ge 50 ]; then
        echo -e "Health Score: ${YELLOW}${HEALTH_SCORE}%${NC} - Fair"
    else
        echo -e "Health Score: ${RED}${HEALTH_SCORE}%${NC} - Poor"
    fi

    echo ""

    # Exit code based on critical failures
    if [ "$CHECKS_FAILED" -gt 0 ]; then
        return 1
    else
        return 0
    fi
}

# Main function
main() {
    echo ""
    echo "========================================"
    echo "GitHub Actions Runner Health Check"
    echo "========================================"

    detect_os

    check_runner_directory
    check_runner_process
    check_service
    check_claude_code
    check_gh_cli
    check_disk_space
    check_network
    check_environment
    check_python
    check_logs

    calculate_health_score
}

# Run main function and capture exit code
main "$@"
EXIT_CODE=$?

echo ""
exit $EXIT_CODE
