#!/usr/bin/env bash
# Lazarus Installation Script
# Installs lazarus-heal and verifies prerequisites

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_MODE=false
REQUIRED_PYTHON_VERSION="3.11"
USE_UV=false

# Helper functions
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

show_help() {
    cat << EOF
Lazarus Installation Script

Usage:
    ./install.sh [OPTIONS]

Options:
    --dev           Install in development mode (editable install)
    -h, --help      Show this help message

Description:
    Installs lazarus-heal and verifies all prerequisites are met.
    For development mode, use --dev to install as editable package.

Prerequisites:
    - Python ${REQUIRED_PYTHON_VERSION}+
    - pip or uv package manager (uv recommended for faster installs)
    - Claude Code (recommended)
    - gh CLI (recommended)

Examples:
    ./install.sh              # Regular user installation
    ./install.sh --dev        # Development installation

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if running on supported OS
check_os() {
    print_header "Checking Operating System"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_success "macOS detected"
        return 0
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "Linux detected"
        return 0
    else
        print_error "Unsupported operating system: $OSTYPE"
        print_info "Lazarus supports macOS and Linux only"
        exit 1
    fi
}

# Check Python version
check_python() {
    print_header "Checking Python"

    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found"
        print_info "Please install Python ${REQUIRED_PYTHON_VERSION} or later"
        exit 1
    fi

    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Found Python $python_version"

    # Compare versions
    local required_major=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f1)
    local required_minor=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f2)
    local current_major=$(echo "$python_version" | cut -d. -f1)
    local current_minor=$(echo "$python_version" | cut -d. -f2)

    if [[ $current_major -lt $required_major ]] || \
       [[ $current_major -eq $required_major && $current_minor -lt $required_minor ]]; then
        print_error "Python ${REQUIRED_PYTHON_VERSION}+ is required, found $python_version"
        exit 1
    fi

    print_success "Python version is compatible"
}

# Check pip/uv
check_pip() {
    print_header "Checking Package Manager"

    # Check for uv first
    if command -v uv &> /dev/null; then
        local uv_version=$(uv --version 2>&1 || echo "unknown")
        print_info "uv $uv_version"
        print_success "uv is available (fast package manager)"
        USE_UV=true
    else
        print_warning "uv not found (recommended for faster installations)"
        print_info "Install with: pip install uv"
        echo ""

        # Fall back to pip
        if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
            print_error "pip not found"
            print_info "Please install pip: python3 -m ensurepip --upgrade"
            exit 1
        fi

        local pip_version=$(python3 -m pip --version)
        print_info "$pip_version"
        print_success "pip is available"
        USE_UV=false
    fi
}

# Check Claude Code (optional but recommended)
check_claude_code() {
    print_header "Checking Claude Code"

    if ! command -v claude &> /dev/null; then
        print_warning "Claude Code not found"
        print_info "Claude Code is required for Lazarus to function"
        print_info "Install from: https://github.com/anthropics/claude-code"
        echo ""
        return 1
    fi

    print_success "Claude Code is installed"

    # Check if authenticated
    if claude --version &> /dev/null; then
        print_success "Claude Code is accessible"
    else
        print_warning "Claude Code may not be properly configured"
        print_info "Please run 'claude auth' to authenticate"
    fi
}

# Check gh CLI (optional but recommended)
check_gh_cli() {
    print_header "Checking GitHub CLI"

    if ! command -v gh &> /dev/null; then
        print_warning "gh CLI not found"
        print_info "gh CLI is required for PR creation features"
        print_info "Install from: https://cli.github.com/"
        echo ""
        return 1
    fi

    print_success "gh CLI is installed"

    # Check if authenticated
    if gh auth status &> /dev/null; then
        print_success "gh CLI is authenticated"
    else
        print_warning "gh CLI is not authenticated"
        print_info "Please run 'gh auth login' to authenticate"
    fi
}

# Check git
check_git() {
    print_header "Checking Git"

    if ! command -v git &> /dev/null; then
        print_error "git not found"
        print_info "Please install git"
        exit 1
    fi

    local git_version=$(git --version)
    print_info "$git_version"
    print_success "Git is installed"
}

# Install lazarus
install_lazarus() {
    print_header "Installing Lazarus"

    if $DEV_MODE; then
        print_info "Installing in development mode (editable install)..."

        if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
            print_error "pyproject.toml not found in $PROJECT_ROOT"
            print_info "Development mode requires installing from source"
            exit 1
        fi

        cd "$PROJECT_ROOT"

        if $USE_UV; then
            uv pip install -e ".[dev]"
        else
            python3 -m pip install -e ".[dev]"
        fi

        print_success "Lazarus installed in development mode"
    else
        print_info "Installing lazarus-heal..."

        # If we're in the project directory with pyproject.toml, install from there
        if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
            cd "$PROJECT_ROOT"

            if $USE_UV; then
                uv pip install .
            else
                python3 -m pip install .
            fi
            print_success "Lazarus installed from source"
        else
            # Otherwise install from PyPI
            if $USE_UV; then
                uv pip install lazarus-heal
            else
                python3 -m pip install lazarus-heal
            fi
            print_success "Lazarus installed from PyPI"
        fi
    fi
}

# Verify installation
verify_installation() {
    print_header "Verifying Installation"

    if ! command -v lazarus &> /dev/null; then
        print_error "lazarus command not found after installation"
        print_info "You may need to add pip's bin directory to your PATH"
        exit 1
    fi

    local version=$(lazarus --version 2>&1 || echo "unknown")
    print_info "Lazarus version: $version"
    print_success "Installation verified successfully"
}

# Print next steps
print_next_steps() {
    print_header "Installation Complete"

    cat << EOF
Lazarus has been installed successfully!

Next steps:

1. Initialize a configuration file:
   ${GREEN}lazarus init${NC}

2. Check prerequisites:
   ${GREEN}lazarus check${NC}

3. Try running a script with healing:
   ${GREEN}lazarus run ./path/to/script.sh${NC}

EOF

    if ! command -v claude &> /dev/null; then
        echo -e "${YELLOW}Note: Claude Code is not installed. Install it from:${NC}"
        echo -e "${BLUE}https://github.com/anthropics/claude-code${NC}\n"
    fi

    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}Note: gh CLI is not installed. Install it for PR features:${NC}"
        echo -e "${BLUE}https://cli.github.com/${NC}\n"
    fi

    if $DEV_MODE; then
        echo -e "${BLUE}Development mode enabled:${NC}"
        echo -e "  - Run tests: ${GREEN}pytest${NC}"
        echo -e "  - Run linting: ${GREEN}ruff check .${NC}"
        echo -e "  - Run type checking: ${GREEN}mypy src/lazarus${NC}"
        echo ""
    fi

    echo -e "Documentation: ${BLUE}https://github.com/boriscardano/lazarus#readme${NC}"
    echo -e "Report issues: ${BLUE}https://github.com/boriscardano/lazarus/issues${NC}"
    echo ""
}

# Main installation flow
main() {
    echo -e "${BLUE}"
    cat << "EOF"
    __    _____  ____  _____  ____  __  __ _____
   / /   / _ \ \/ /\ \/ / _ \/ ___||  \/  / ____|
  / /   | |_| |  \  \  / |_| \  \  | |\/| |  _|
 / /    |  _  /  /  /  |  _  /  /  | |  | | |___
/_/     |_| |_/_/\_/\_/|_| |_/\_\  |_|  |_|_____|

Self-Healing Script Runner powered by Claude Code

EOF
    echo -e "${NC}"

    # Run checks
    check_os
    check_python
    check_pip
    check_git

    # Optional checks
    check_claude_code
    check_gh_cli

    # Install
    install_lazarus

    # Verify
    verify_installation

    # Print next steps
    print_next_steps
}

# Run main installation
main
