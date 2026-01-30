#!/usr/bin/env bash
# Lazarus Uninstallation Script
# Removes lazarus-heal and optionally removes configuration files

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script variables
REMOVE_CONFIG=false
FORCE_MODE=false
CONFIG_DIR="$HOME/.lazarus"
HISTORY_FILE="$HOME/.lazarus-history"
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
Lazarus Uninstallation Script

Usage:
    ./uninstall.sh [OPTIONS]

Options:
    --remove-config     Remove configuration files and history
    --force             Skip confirmation prompts
    -h, --help          Show this help message

Description:
    Uninstalls lazarus-heal from your system. Optionally removes
    user configuration files and healing history.

Configuration files:
    - ~/.lazarus/           Configuration directory
    - ~/.lazarus-history    Healing history file

Examples:
    ./uninstall.sh                      # Uninstall, keep config
    ./uninstall.sh --remove-config      # Uninstall and remove config
    ./uninstall.sh --remove-config --force  # No prompts

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-config)
            REMOVE_CONFIG=true
            shift
            ;;
        --force)
            FORCE_MODE=true
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

# Confirm uninstallation
confirm_uninstall() {
    if $FORCE_MODE; then
        return 0
    fi

    print_header "Uninstall Confirmation"

    echo -e "${YELLOW}This will uninstall Lazarus from your system.${NC}"

    if $REMOVE_CONFIG; then
        echo -e "${RED}This will also DELETE the following:${NC}"
        [[ -d "$CONFIG_DIR" ]] && echo "  - $CONFIG_DIR"
        [[ -f "$HISTORY_FILE" ]] && echo "  - $HISTORY_FILE"
        echo ""
    fi

    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        print_info "Uninstallation cancelled"
        exit 0
    fi
}

# Check if lazarus is installed
check_installation() {
    print_header "Checking Installation"

    # Check for uv first
    if command -v uv &> /dev/null; then
        USE_UV=true
        if ! uv pip show lazarus-heal &> /dev/null; then
            print_warning "Lazarus (lazarus-heal) is not installed via uv/pip"

            if command -v lazarus &> /dev/null; then
                print_info "However, 'lazarus' command is available"
                print_info "It may be installed from source or in development mode"
            else
                print_error "Lazarus does not appear to be installed"
                exit 1
            fi
        else
            print_success "Lazarus is installed"
        fi
    else
        USE_UV=false
        if ! python3 -m pip show lazarus-heal &> /dev/null; then
            print_warning "Lazarus (lazarus-heal) is not installed via pip"

            if command -v lazarus &> /dev/null; then
                print_info "However, 'lazarus' command is available"
                print_info "It may be installed from source or in development mode"
            else
                print_error "Lazarus does not appear to be installed"
                exit 1
            fi
        else
            print_success "Lazarus is installed"
        fi
    fi
}

# Uninstall lazarus package
uninstall_package() {
    print_header "Uninstalling Lazarus"

    print_info "Removing lazarus-heal package..."

    if $USE_UV; then
        if uv pip uninstall -y lazarus-heal 2>&1 | grep -q "not installed"; then
            print_warning "Package not found, may be installed in dev mode"

            # Try to find and uninstall by package name variations
            for pkg in "lazarus" "lazarus-heal"; do
                if uv pip show "$pkg" &> /dev/null; then
                    uv pip uninstall -y "$pkg"
                    break
                fi
            done
        fi
    else
        if python3 -m pip uninstall -y lazarus-heal 2>&1 | grep -q "not installed"; then
            print_warning "Package not found in pip, may be installed in dev mode"

            # Try to find and uninstall by package name variations
            for pkg in "lazarus" "lazarus-heal"; do
                if python3 -m pip show "$pkg" &> /dev/null; then
                    python3 -m pip uninstall -y "$pkg"
                    break
                fi
            done
        fi
    fi

    # Verify uninstallation
    if command -v lazarus &> /dev/null; then
        print_warning "lazarus command still available - may be cached in shell"
        print_info "Try running: hash -r"
    else
        print_success "Lazarus package uninstalled successfully"
    fi
}

# Remove configuration files
remove_config_files() {
    if ! $REMOVE_CONFIG; then
        print_info "Keeping configuration files (use --remove-config to remove)"
        return 0
    fi

    print_header "Removing Configuration Files"

    local removed_any=false

    # Remove config directory
    if [[ -d "$CONFIG_DIR" ]]; then
        print_info "Removing $CONFIG_DIR..."
        rm -rf "$CONFIG_DIR"
        print_success "Removed configuration directory"
        removed_any=true
    else
        print_info "Configuration directory not found: $CONFIG_DIR"
    fi

    # Remove history file
    if [[ -f "$HISTORY_FILE" ]]; then
        print_info "Removing $HISTORY_FILE..."
        rm -f "$HISTORY_FILE"
        print_success "Removed history file"
        removed_any=true
    else
        print_info "History file not found: $HISTORY_FILE"
    fi

    if $removed_any; then
        print_success "Configuration files removed"
    else
        print_info "No configuration files found"
    fi
}

# Find and list project config files
list_project_configs() {
    print_header "Project Configuration Files"

    print_info "The following project-level config files were NOT removed:"
    echo ""
    echo "  - lazarus.yaml (in your project directories)"
    echo "  - .lazarus/ (project-specific config)"
    echo ""
    print_info "Remove these manually if no longer needed"
}

# Print completion message
print_completion() {
    print_header "Uninstallation Complete"

    cat << EOF
Lazarus has been uninstalled from your system.

EOF

    if $REMOVE_CONFIG; then
        echo -e "${GREEN}User configuration files have been removed.${NC}"
        echo ""
    else
        echo -e "${BLUE}Configuration files were preserved at:${NC}"
        [[ -d "$CONFIG_DIR" ]] && echo "  - $CONFIG_DIR"
        [[ -f "$HISTORY_FILE" ]] && echo "  - $HISTORY_FILE"
        echo ""
        echo -e "${YELLOW}To remove these files, run:${NC}"
        echo -e "  ./uninstall.sh --remove-config"
        echo ""
    fi

    echo -e "To reinstall Lazarus:"
    echo -e "  ${GREEN}pip install lazarus-heal${NC}"
    echo ""
    echo -e "Thank you for using Lazarus!"
    echo ""
}

# Clean up shell hash cache
cleanup_shell_cache() {
    print_header "Cleaning Up"

    print_info "Clearing shell command cache..."

    # Clear hash cache for bash/zsh
    if [[ -n "$BASH_VERSION" ]]; then
        hash -r 2>/dev/null || true
    elif [[ -n "$ZSH_VERSION" ]]; then
        rehash 2>/dev/null || true
    fi

    print_success "Shell cache cleared"
}

# Main uninstallation flow
main() {
    echo -e "${BLUE}"
    cat << "EOF"
    __    _____  ____  _____  ____  __  __ _____
   / /   / _ \ \/ /\ \/ / _ \/ ___||  \/  / ____|
  / /   | |_| |  \  \  / |_| \  \  | |\/| |  _|
 / /    |  _  /  /  /  |  _  /  /  | |  | | |___
/_/     |_| |_/_/\_/\_/|_| |_/\_\  |_|  |_|_____|

Uninstallation Script

EOF
    echo -e "${NC}"

    # Confirm with user
    confirm_uninstall

    # Check installation
    check_installation

    # Uninstall package
    uninstall_package

    # Remove config if requested
    remove_config_files

    # Clean up shell cache
    cleanup_shell_cache

    # List remaining files
    if ! $REMOVE_CONFIG; then
        list_project_configs
    fi

    # Print completion message
    print_completion
}

# Run main uninstallation
main
