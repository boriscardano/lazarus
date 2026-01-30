#!/usr/bin/env bash
#
# install-runner.sh
# Cross-platform GitHub Actions runner installation script
#
# This script automates the installation and configuration of a
# GitHub Actions self-hosted runner on macOS and Linux systems.
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub runner version
RUNNER_VERSION="2.313.0"

# Functions for colored output
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running with appropriate permissions
check_permissions() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - should not run as root
        if [[ $EUID -eq 0 ]]; then
            error "This script should not be run as root on macOS"
            exit 1
        fi
    else
        # Linux - check if we can use sudo
        if ! sudo -n true 2>/dev/null; then
            warning "This script requires sudo access. You may be prompted for your password."
        fi
    fi
}

# Detect operating system and architecture
detect_system() {
    info "Detecting system configuration..."

    OS_TYPE=""
    ARCH=""

    case "$OSTYPE" in
        darwin*)
            OS_TYPE="osx"
            info "Operating System: macOS"
            ;;
        linux*)
            OS_TYPE="linux"
            info "Operating System: Linux"

            # Detect Linux distribution
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                info "Distribution: $NAME $VERSION"
            fi
            ;;
        *)
            error "Unsupported operating system: $OSTYPE"
            exit 1
            ;;
    esac

    # Detect architecture
    MACHINE=$(uname -m)
    case "$MACHINE" in
        x86_64|amd64)
            ARCH="x64"
            info "Architecture: x64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            info "Architecture: ARM64"
            ;;
        *)
            error "Unsupported architecture: $MACHINE"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    local missing_deps=()

    # Check for required commands
    for cmd in curl tar; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # Check for git
    if ! command -v git &> /dev/null; then
        warning "git is not installed (recommended for development workflows)"
    fi

    # Check for jq (nice to have)
    if ! command -v jq &> /dev/null; then
        warning "jq is not installed (recommended for JSON parsing)"
    fi

    # Check for gh CLI (recommended)
    if ! command -v gh &> /dev/null; then
        warning "GitHub CLI (gh) is not installed (recommended for easier configuration)"
        warning "Install from: https://cli.github.com/"
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        echo ""

        if [[ "$OS_TYPE" == "linux" ]]; then
            info "Install with:"
            echo "  Ubuntu/Debian: sudo apt install ${missing_deps[*]}"
            echo "  RHEL/CentOS:   sudo dnf install ${missing_deps[*]}"
        elif [[ "$OS_TYPE" == "osx" ]]; then
            info "Install with Homebrew:"
            echo "  brew install ${missing_deps[*]}"
        fi

        exit 1
    fi

    success "All required prerequisites are installed"
}

# Get repository information
get_repo_info() {
    echo ""
    info "Repository Configuration"
    echo ""

    # Try to detect from gh CLI
    if command -v gh &> /dev/null && gh auth status &> /dev/null; then
        info "GitHub CLI is authenticated"

        # Try to get current repo
        if CURRENT_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null); then
            info "Detected repository: $CURRENT_REPO"
            read -p "Use this repository? [Y/n] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                REPO_URL="https://github.com/$CURRENT_REPO"
            fi
        fi
    fi

    # Get repository URL
    if [ -z "${REPO_URL:-}" ]; then
        read -p "Enter repository URL (e.g., https://github.com/owner/repo): " REPO_URL
    fi

    # Validate URL format
    if [[ ! "$REPO_URL" =~ ^https://github\.com/[^/]+/[^/]+$ ]]; then
        error "Invalid repository URL format"
        error "Expected: https://github.com/owner/repo"
        exit 1
    fi

    success "Repository URL: $REPO_URL"

    # Get registration token
    echo ""
    info "You need a runner registration token from GitHub"
    echo "  1. Go to: $REPO_URL/settings/actions/runners/new"
    echo "  2. Copy the registration token"
    echo ""

    # Try to generate token with gh CLI
    if command -v gh &> /dev/null && gh auth status &> /dev/null; then
        info "Attempting to generate token automatically..."

        REPO_OWNER=$(echo "$REPO_URL" | sed 's#https://github.com/\([^/]*\)/.*#\1#')
        REPO_NAME=$(echo "$REPO_URL" | sed 's#https://github.com/[^/]*/\([^/]*\)#\1#')

        if TOKEN=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/actions/runners/registration-token --jq .token 2>/dev/null); then
            success "Token generated automatically"
            REG_TOKEN="$TOKEN"
        else
            warning "Could not generate token automatically"
            read -sp "Enter registration token: " REG_TOKEN
            echo
        fi
    else
        read -sp "Enter registration token: " REG_TOKEN
        echo
    fi

    if [ -z "$REG_TOKEN" ]; then
        error "Registration token is required"
        exit 1
    fi

    success "Registration token received"
}

# Create runner directory
create_runner_directory() {
    info "Creating runner directory..."

    if [[ "$OS_TYPE" == "osx" ]]; then
        RUNNER_DIR="$HOME/actions-runner"
    else
        # Linux - check if we're setting up for a dedicated user
        read -p "Create dedicated user 'actions-runner'? [Y/n] " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if ! id -u actions-runner &> /dev/null; then
                info "Creating user 'actions-runner'..."
                sudo useradd -m -s /bin/bash actions-runner
                success "User 'actions-runner' created"
            else
                info "User 'actions-runner' already exists"
            fi
            RUNNER_DIR="/home/actions-runner/actions-runner"
            RUNNER_USER="actions-runner"
        else
            RUNNER_DIR="$HOME/actions-runner"
            RUNNER_USER="$USER"
        fi
    fi

    # Create directory
    if [ "$RUNNER_USER" != "$USER" ]; then
        sudo mkdir -p "$RUNNER_DIR"
        sudo chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"
    else
        mkdir -p "$RUNNER_DIR"
    fi

    success "Runner directory created: $RUNNER_DIR"
}

# Download and extract runner
download_runner() {
    info "Downloading GitHub Actions runner v$RUNNER_VERSION..."

    DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-${OS_TYPE}-${ARCH}-${RUNNER_VERSION}.tar.gz"
    DOWNLOAD_FILE="actions-runner-${OS_TYPE}-${ARCH}.tar.gz"

    # Download
    if curl -L -o "/tmp/$DOWNLOAD_FILE" "$DOWNLOAD_URL"; then
        success "Runner downloaded successfully"
    else
        error "Failed to download runner"
        exit 1
    fi

    # Extract
    info "Extracting runner..."

    if [ "$RUNNER_USER" != "$USER" ]; then
        sudo tar xzf "/tmp/$DOWNLOAD_FILE" -C "$RUNNER_DIR"
        sudo chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"
    else
        tar xzf "/tmp/$DOWNLOAD_FILE" -C "$RUNNER_DIR"
    fi

    # Cleanup
    rm "/tmp/$DOWNLOAD_FILE"

    success "Runner extracted to $RUNNER_DIR"
}

# Configure runner
configure_runner() {
    info "Configuring runner..."

    # Get runner name
    DEFAULT_NAME=$(hostname -s)
    read -p "Enter runner name (default: $DEFAULT_NAME): " RUNNER_NAME
    RUNNER_NAME=${RUNNER_NAME:-$DEFAULT_NAME}

    # Get labels
    DEFAULT_LABELS="self-hosted,$OS_TYPE,$ARCH"
    read -p "Enter runner labels (default: $DEFAULT_LABELS): " RUNNER_LABELS
    RUNNER_LABELS=${RUNNER_LABELS:-$DEFAULT_LABELS}

    # Run configuration
    info "Running runner configuration..."

    CONFIG_CMD="cd $RUNNER_DIR && ./config.sh --url $REPO_URL --token $REG_TOKEN --name $RUNNER_NAME --labels $RUNNER_LABELS --unattended"

    if [ "$RUNNER_USER" != "$USER" ]; then
        sudo -u "$RUNNER_USER" bash -c "$CONFIG_CMD"
    else
        bash -c "$CONFIG_CMD"
    fi

    success "Runner configured successfully"
}

# Test runner
test_runner() {
    echo ""
    read -p "Test runner now? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        info "Starting runner for testing (press Ctrl+C to stop)..."

        if [ "$RUNNER_USER" != "$USER" ]; then
            sudo -u "$RUNNER_USER" bash -c "cd $RUNNER_DIR && ./run.sh"
        else
            (cd "$RUNNER_DIR" && ./run.sh)
        fi
    fi
}

# Setup as service
setup_service() {
    echo ""
    read -p "Configure runner as a system service? [Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

        if [[ "$OS_TYPE" == "osx" ]]; then
            info "Setting up LaunchAgent service..."
            if [ -f "$SCRIPT_DIR/configure-launchd.sh" ]; then
                bash "$SCRIPT_DIR/configure-launchd.sh"
            else
                warning "LaunchAgent setup script not found"
                info "Run: $SCRIPT_DIR/configure-launchd.sh"
            fi
        else
            info "Setting up systemd service..."
            if [ -f "$SCRIPT_DIR/configure-systemd.sh" ]; then
                sudo bash "$SCRIPT_DIR/configure-systemd.sh"
            else
                warning "systemd setup script not found"
                info "Run: sudo $SCRIPT_DIR/configure-systemd.sh"
            fi
        fi
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "========================================"
    success "Runner Installation Complete!"
    echo "========================================"
    echo ""
    echo "Runner Details:"
    echo "  - Directory: $RUNNER_DIR"
    echo "  - Repository: $REPO_URL"
    echo "  - Name: ${RUNNER_NAME:-$(hostname -s)}"
    echo "  - Labels: ${RUNNER_LABELS:-$DEFAULT_LABELS}"
    echo ""
    echo "Next Steps:"
    echo "  1. Verify runner appears in GitHub:"
    echo "     $REPO_URL/settings/actions/runners"
    echo ""
    echo "  2. Install Claude Code:"
    echo "     pip install claude-code"
    echo "     claude auth login"
    echo ""
    echo "  3. Test with a workflow:"
    echo "     runs-on: self-hosted"
    echo ""
    echo "Useful Commands:"

    if [[ "$OS_TYPE" == "osx" ]]; then
        echo "  Start:   launchctl start com.github.actions.runner"
        echo "  Stop:    launchctl stop com.github.actions.runner"
        echo "  Status:  launchctl list | grep github.actions.runner"
        echo "  Logs:    tail -f $RUNNER_DIR/runner.log"
    else
        echo "  Start:   sudo systemctl start actions-runner"
        echo "  Stop:    sudo systemctl stop actions-runner"
        echo "  Status:  sudo systemctl status actions-runner"
        echo "  Logs:    sudo journalctl -u actions-runner -f"
    fi

    echo ""
    echo "Documentation:"
    echo "  macOS: runner-setup/docs/macos-guide.md"
    echo "  Linux: runner-setup/docs/linux-guide.md"
    echo ""
}

# Main installation flow
main() {
    echo ""
    echo "========================================"
    echo "GitHub Actions Runner Installation"
    echo "========================================"
    echo ""

    check_permissions
    detect_system
    check_prerequisites
    get_repo_info
    create_runner_directory
    download_runner
    configure_runner
    test_runner
    setup_service
    print_summary
}

# Run main function
main "$@"
