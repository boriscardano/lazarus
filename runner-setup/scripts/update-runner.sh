#!/usr/bin/env bash
#
# update-runner.sh
# Update script for GitHub Actions runner and Lazarus
#
# This script safely updates the runner binary, Lazarus components,
# and dependencies while minimizing downtime.
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Output functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
header() { echo -e "\n${BOLD}$1${NC}\n"; }

# Flags
DRY_RUN=false
SKIP_RUNNER=false
SKIP_LAZARUS=false
SKIP_CLAUDE=false
AUTO_YES=false

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-runner)
                SKIP_RUNNER=true
                shift
                ;;
            --skip-lazarus)
                SKIP_LAZARUS=true
                shift
                ;;
            --skip-claude)
                SKIP_CLAUDE=true
                shift
                ;;
            -y|--yes)
                AUTO_YES=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help
show_help() {
    cat << EOF
Update GitHub Actions Runner and Lazarus

Usage: $0 [OPTIONS]

Options:
    --dry-run           Show what would be updated without making changes
    --skip-runner       Skip runner binary update
    --skip-lazarus      Skip Lazarus update
    --skip-claude       Skip Claude Code update
    -y, --yes           Automatic yes to prompts
    -h, --help          Show this help message

Examples:
    $0                  # Interactive update of everything
    $0 --dry-run        # Check for updates without applying
    $0 --skip-runner    # Update Lazarus and Claude Code only
    $0 -y               # Non-interactive update
EOF
}

# Detect OS and configuration
detect_system() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="osx"
        SERVICE_NAME="com.github.actions.runner"
        RUNNER_DIR="$HOME/actions-runner"
        IS_SYSTEMD=false
    else
        OS_TYPE="linux"
        SERVICE_NAME="actions-runner"
        IS_SYSTEMD=true

        if [ -d "/home/actions-runner/actions-runner" ]; then
            RUNNER_DIR="/home/actions-runner/actions-runner"
            RUNNER_USER="actions-runner"
        else
            RUNNER_DIR="$HOME/actions-runner"
            RUNNER_USER="$USER"
        fi
    fi

    # Detect architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64) ARCH="x64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        *) error "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
}

# Check current runner version
check_runner_version() {
    header "Checking Runner Version"

    if [ ! -f "$RUNNER_DIR/bin/Runner.Listener" ]; then
        error "Runner not found at: $RUNNER_DIR"
        return 1
    fi

    # Get current version
    CURRENT_VERSION="unknown"
    if [ -f "$RUNNER_DIR/.setup_info" ]; then
        CURRENT_VERSION=$(grep -o '"version":"[^"]*"' "$RUNNER_DIR/.setup_info" | cut -d'"' -f4 || echo "unknown")
    fi

    info "Current version: $CURRENT_VERSION"

    # Get latest version from GitHub
    info "Checking for latest version..."

    if command -v curl &> /dev/null; then
        LATEST_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | grep '"tag_name"' | cut -d'"' -f4 | sed 's/v//' || echo "unknown")

        if [ "$LATEST_VERSION" != "unknown" ]; then
            info "Latest version: $LATEST_VERSION"

            if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
                success "Runner is already up to date"
                RUNNER_UPDATE_NEEDED=false
            else
                warning "Runner update available: $CURRENT_VERSION -> $LATEST_VERSION"
                RUNNER_UPDATE_NEEDED=true
            fi
        else
            warning "Could not determine latest version"
            RUNNER_UPDATE_NEEDED=false
        fi
    else
        warning "curl not available, skipping version check"
        RUNNER_UPDATE_NEEDED=false
    fi
}

# Check Claude Code version
check_claude_version() {
    header "Checking Claude Code Version"

    if ! command -v claude &> /dev/null; then
        warning "Claude Code not installed"
        CLAUDE_UPDATE_NEEDED=false
        return
    fi

    CURRENT_CLAUDE=$(claude --version 2>/dev/null || echo "unknown")
    info "Current version: $CURRENT_CLAUDE"

    # Check for updates via pip
    if command -v pip3 &> /dev/null; then
        info "Checking for updates..."

        OUTDATED=$(pip3 list --outdated 2>/dev/null | grep claude-code || true)

        if [ -n "$OUTDATED" ]; then
            warning "Claude Code update available"
            CLAUDE_UPDATE_NEEDED=true
        else
            success "Claude Code is up to date"
            CLAUDE_UPDATE_NEEDED=false
        fi
    else
        warning "pip3 not available, skipping version check"
        CLAUDE_UPDATE_NEEDED=false
    fi
}

# Check Lazarus version
check_lazarus_version() {
    header "Checking Lazarus Version"

    # Try to find Lazarus installation
    LAZARUS_DIR=""

    # Common locations
    for dir in "$HOME/lazarus" "/opt/lazarus" "/usr/local/lazarus"; do
        if [ -d "$dir/.git" ]; then
            LAZARUS_DIR="$dir"
            break
        fi
    done

    if [ -z "$LAZARUS_DIR" ]; then
        warning "Lazarus installation not found"
        LAZARUS_UPDATE_NEEDED=false
        return
    fi

    info "Lazarus directory: $LAZARUS_DIR"

    # Check git status
    cd "$LAZARUS_DIR"

    CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    info "Current branch: $CURRENT_BRANCH"
    info "Current commit: $CURRENT_COMMIT"

    # Fetch latest
    if git fetch origin &> /dev/null; then
        REMOTE_COMMIT=$(git rev-parse --short origin/"$CURRENT_BRANCH" 2>/dev/null || echo "unknown")

        if [ "$CURRENT_COMMIT" != "$REMOTE_COMMIT" ]; then
            warning "Lazarus update available: $CURRENT_COMMIT -> $REMOTE_COMMIT"
            LAZARUS_UPDATE_NEEDED=true
        else
            success "Lazarus is up to date"
            LAZARUS_UPDATE_NEEDED=false
        fi
    else
        warning "Could not fetch latest version"
        LAZARUS_UPDATE_NEEDED=false
    fi
}

# Stop runner service
stop_service() {
    header "Stopping Runner Service"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would stop service"
        return
    fi

    if [ "$IS_SYSTEMD" = true ]; then
        if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            info "Stopping systemd service..."
            sudo systemctl stop "$SERVICE_NAME"
            success "Service stopped"
        else
            info "Service is not running"
        fi
    else
        if launchctl list | grep -q "$SERVICE_NAME" 2>/dev/null; then
            info "Stopping LaunchAgent..."
            launchctl stop "$SERVICE_NAME"
            success "Service stopped"
        else
            info "Service is not running"
        fi
    fi

    # Wait for process to stop
    sleep 2

    # Force kill if still running
    if pgrep -f "actions-runner.*run.sh" > /dev/null; then
        warning "Runner process still running, force stopping..."
        pkill -f "actions-runner.*run.sh" || true
        sleep 1
    fi
}

# Update runner binary
update_runner() {
    header "Updating Runner Binary"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would update runner to version $LATEST_VERSION"
        return
    fi

    # Download new version
    DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${LATEST_VERSION}/actions-runner-${OS_TYPE}-${ARCH}-${LATEST_VERSION}.tar.gz"
    DOWNLOAD_FILE="/tmp/actions-runner-${OS_TYPE}-${ARCH}.tar.gz"

    info "Downloading runner v$LATEST_VERSION..."

    if ! curl -L -o "$DOWNLOAD_FILE" "$DOWNLOAD_URL"; then
        error "Failed to download runner"
        return 1
    fi

    success "Download complete"

    # Backup current runner
    info "Creating backup..."
    BACKUP_DIR="${RUNNER_DIR}_backup_$(date +%Y%m%d_%H%M%S)"

    if [ "$RUNNER_USER" != "$USER" ]; then
        sudo cp -r "$RUNNER_DIR" "$BACKUP_DIR"
    else
        cp -r "$RUNNER_DIR" "$BACKUP_DIR"
    fi

    success "Backup created: $BACKUP_DIR"

    # Extract new version
    info "Extracting new version..."

    if [ "$RUNNER_USER" != "$USER" ]; then
        sudo tar xzf "$DOWNLOAD_FILE" -C "$RUNNER_DIR"
        sudo chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"
    else
        tar xzf "$DOWNLOAD_FILE" -C "$RUNNER_DIR"
    fi

    # Cleanup
    rm "$DOWNLOAD_FILE"

    success "Runner updated to v$LATEST_VERSION"

    # Keep backup info
    echo "$BACKUP_DIR" > /tmp/lazarus_runner_backup.txt
}

# Update Claude Code
update_claude() {
    header "Updating Claude Code"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would update Claude Code"
        return
    fi

    # Check for virtual environment
    VENV_DIR=""
    if [ -d "$HOME/claude-env" ]; then
        VENV_DIR="$HOME/claude-env"
    elif [ -d "/home/actions-runner/claude-env" ]; then
        VENV_DIR="/home/actions-runner/claude-env"
    fi

    if [ -n "$VENV_DIR" ]; then
        info "Updating in virtual environment: $VENV_DIR"

        if [ "$RUNNER_USER" != "$USER" ]; then
            sudo -u "$RUNNER_USER" bash -c "source $VENV_DIR/bin/activate && pip install --upgrade claude-code"
        else
            source "$VENV_DIR/bin/activate"
            pip install --upgrade claude-code
            deactivate
        fi
    else
        info "Updating system-wide installation..."
        pip3 install --upgrade claude-code
    fi

    success "Claude Code updated"
}

# Update Lazarus
update_lazarus() {
    header "Updating Lazarus"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would update Lazarus"
        return
    fi

    if [ -z "$LAZARUS_DIR" ]; then
        warning "Lazarus directory not found, skipping"
        return
    fi

    cd "$LAZARUS_DIR"

    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        info "Stashing local changes..."
        git stash
    fi

    # Pull latest
    info "Pulling latest changes..."
    git pull origin "$CURRENT_BRANCH"

    success "Lazarus updated"
}

# Start runner service
start_service() {
    header "Starting Runner Service"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would start service"
        return
    fi

    if [ "$IS_SYSTEMD" = true ]; then
        info "Starting systemd service..."
        sudo systemctl start "$SERVICE_NAME"
        sleep 2

        if systemctl is-active --quiet "$SERVICE_NAME"; then
            success "Service started"
        else
            error "Failed to start service"
            info "Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
            return 1
        fi
    else
        info "Starting LaunchAgent..."
        launchctl start "$SERVICE_NAME"
        sleep 2

        if launchctl list | grep -q "$SERVICE_NAME"; then
            success "Service started"
        else
            error "Failed to start service"
            return 1
        fi
    fi
}

# Verify update
verify_update() {
    header "Verifying Update"

    # Check runner process
    if pgrep -f "actions-runner.*run.sh" > /dev/null; then
        success "Runner process is running"
    else
        warning "Runner process not found"
    fi

    # Check version
    if [ ! "$SKIP_RUNNER" = true ] && [ "$RUNNER_UPDATE_NEEDED" = true ]; then
        UPDATED_VERSION=$(grep -o '"version":"[^"]*"' "$RUNNER_DIR/.setup_info" | cut -d'"' -f4 || echo "unknown")
        info "Updated runner version: $UPDATED_VERSION"
    fi

    # Check Claude Code
    if [ ! "$SKIP_CLAUDE" = true ] && [ "$CLAUDE_UPDATE_NEEDED" = true ]; then
        UPDATED_CLAUDE=$(claude --version 2>/dev/null || echo "unknown")
        info "Updated Claude Code version: $UPDATED_CLAUDE"
    fi

    success "Update verification complete"
}

# Cleanup old backups
cleanup_backups() {
    header "Cleaning Up Old Backups"

    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] Would cleanup old backups"
        return
    fi

    # Find backups older than 7 days
    BACKUP_PATTERN="${RUNNER_DIR}_backup_*"
    OLD_BACKUPS=$(find "$(dirname "$RUNNER_DIR")" -maxdepth 1 -type d -name "$(basename "$RUNNER_DIR")_backup_*" -mtime +7 2>/dev/null || true)

    if [ -n "$OLD_BACKUPS" ]; then
        echo "$OLD_BACKUPS" | while read -r backup; do
            info "Removing old backup: $backup"
            rm -rf "$backup"
        done
        success "Old backups cleaned up"
    else
        info "No old backups to clean up"
    fi
}

# Print summary
print_summary() {
    header "Update Summary"

    echo "Updates Applied:"

    if [ "$SKIP_RUNNER" = true ]; then
        echo "  Runner:  Skipped"
    elif [ "$RUNNER_UPDATE_NEEDED" = true ]; then
        echo "  Runner:  Updated to v$LATEST_VERSION"
    else
        echo "  Runner:  Already up to date"
    fi

    if [ "$SKIP_CLAUDE" = true ]; then
        echo "  Claude:  Skipped"
    elif [ "$CLAUDE_UPDATE_NEEDED" = true ]; then
        echo "  Claude:  Updated"
    else
        echo "  Claude:  Already up to date"
    fi

    if [ "$SKIP_LAZARUS" = true ]; then
        echo "  Lazarus: Skipped"
    elif [ "$LAZARUS_UPDATE_NEEDED" = true ]; then
        echo "  Lazarus: Updated"
    else
        echo "  Lazarus: Already up to date"
    fi

    echo ""

    if [ -f /tmp/lazarus_runner_backup.txt ]; then
        BACKUP_DIR=$(cat /tmp/lazarus_runner_backup.txt)
        echo "Backup Location: $BACKUP_DIR"
        echo ""
        echo "To rollback: rm -rf $RUNNER_DIR && mv $BACKUP_DIR $RUNNER_DIR"
        rm /tmp/lazarus_runner_backup.txt
    fi

    echo ""
    success "Update complete!"
}

# Main function
main() {
    echo ""
    echo "========================================"
    echo "Runner & Lazarus Update Script"
    echo "========================================"

    detect_system

    # Check for updates
    if [ "$SKIP_RUNNER" != true ]; then
        check_runner_version
    fi

    if [ "$SKIP_CLAUDE" != true ]; then
        check_claude_version
    fi

    if [ "$SKIP_LAZARUS" != true ]; then
        check_lazarus_version
    fi

    # Confirm update
    if [ "$DRY_RUN" = true ]; then
        info "Dry run mode - no changes will be made"
    elif [ "$AUTO_YES" != true ]; then
        echo ""
        read -p "Proceed with update? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Update cancelled"
            exit 0
        fi
    fi

    # Perform updates
    UPDATES_MADE=false

    if [ "$SKIP_RUNNER" != true ] && [ "$RUNNER_UPDATE_NEEDED" = true ]; then
        stop_service
        update_runner
        UPDATES_MADE=true
    fi

    if [ "$SKIP_CLAUDE" != true ] && [ "$CLAUDE_UPDATE_NEEDED" = true ]; then
        update_claude
        UPDATES_MADE=true
    fi

    if [ "$SKIP_LAZARUS" != true ] && [ "$LAZARUS_UPDATE_NEEDED" = true ]; then
        update_lazarus
        UPDATES_MADE=true
    fi

    # Restart service if updates were made
    if [ "$UPDATES_MADE" = true ] && [ "$DRY_RUN" != true ]; then
        start_service
        verify_update
        cleanup_backups
    fi

    print_summary
}

# Parse arguments and run
parse_args "$@"
main
