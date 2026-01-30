#!/usr/bin/env bash
# Lazarus Update Script
# Updates lazarus-heal to the latest version

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
INSTALL_TYPE=""  # "pip", "source", or "dev"
FORCE_MODE=false
SKIP_MIGRATIONS=false
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
Lazarus Update Script

Usage:
    ./update.sh [OPTIONS]

Options:
    --force             Force update without confirmation
    --skip-migrations   Skip running migrations
    -h, --help          Show this help message

Description:
    Updates Lazarus to the latest version. Automatically detects
    installation type (pip, source, or development) and updates
    accordingly.

Installation types:
    - pip: Installed via 'pip install lazarus-heal'
    - source: Installed from git repository
    - dev: Installed in development mode with 'pip install -e .'

Examples:
    ./update.sh                 # Update with confirmation
    ./update.sh --force         # Update without prompts
    ./update.sh --skip-migrations  # Skip migrations

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_MODE=true
            shift
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
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

# Check if lazarus is installed
check_installation() {
    print_header "Checking Installation"

    if ! command -v lazarus &> /dev/null; then
        print_error "Lazarus is not installed"
        print_info "Install it first with: ./scripts/install.sh"
        exit 1
    fi

    print_success "Lazarus is installed"

    # Check for uv
    if command -v uv &> /dev/null; then
        print_info "Using uv for faster updates"
        USE_UV=true
    else
        print_info "Using pip (install 'uv' for faster updates: pip install uv)"
        USE_UV=false
    fi
}

# Get current version
get_current_version() {
    print_header "Current Version"

    local version=$(lazarus --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    echo -e "${BLUE}Current version: ${GREEN}$version${NC}"

    # Store for later comparison
    CURRENT_VERSION=$version
}

# Detect installation type
detect_install_type() {
    print_header "Detecting Installation Type"

    # Check if installed via pip
    if python3 -m pip show lazarus-heal &> /dev/null; then
        local install_location=$(python3 -m pip show lazarus-heal | grep "Location:" | cut -d: -f2- | xargs)

        # Check if it's an editable install
        if python3 -m pip show lazarus-heal | grep -q "Editable project location:"; then
            INSTALL_TYPE="dev"
            print_info "Installation type: Development (editable)"
        # Check if we're in a git repo
        elif [[ -d "$PROJECT_ROOT/.git" ]]; then
            INSTALL_TYPE="source"
            print_info "Installation type: Source (from git)"
        else
            INSTALL_TYPE="pip"
            print_info "Installation type: PyPI (pip)"
        fi
    else
        print_error "Could not determine installation type"
        exit 1
    fi

    echo ""
}

# Confirm update
confirm_update() {
    if $FORCE_MODE; then
        return 0
    fi

    print_header "Update Confirmation"

    case $INSTALL_TYPE in
        pip)
            echo -e "${BLUE}This will update Lazarus from PyPI${NC}"
            ;;
        source)
            echo -e "${BLUE}This will pull latest changes from git and reinstall${NC}"
            ;;
        dev)
            echo -e "${BLUE}This will pull latest changes from git (dev mode)${NC}"
            ;;
    esac

    echo ""
    read -p "Continue with update? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        print_info "Update cancelled"
        exit 0
    fi
}

# Update from PyPI
update_from_pip() {
    print_header "Updating from PyPI"

    if $USE_UV; then
        print_info "Running: uv pip install --upgrade lazarus-heal"
        uv pip install --upgrade lazarus-heal
    else
        print_info "Running: pip install --upgrade lazarus-heal"
        python3 -m pip install --upgrade lazarus-heal
    fi

    print_success "Updated from PyPI"
}

# Update from source (git)
update_from_source() {
    print_header "Updating from Source"

    if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
        print_error "Not a git repository: $PROJECT_ROOT"
        print_info "Cannot update from source"
        exit 1
    fi

    cd "$PROJECT_ROOT"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "You have uncommitted changes"
        if ! $FORCE_MODE; then
            read -p "Stash changes and continue? (yes/no): " -r
            echo ""
            if [[ $REPLY =~ ^[Yy]es$ ]]; then
                git stash push -m "Lazarus update script - $(date +%Y-%m-%d-%H-%M-%S)"
                print_info "Changes stashed"
            else
                print_error "Update cancelled"
                exit 1
            fi
        fi
    fi

    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    print_info "Current branch: $current_branch"

    # Pull latest changes
    print_info "Pulling latest changes..."
    if git pull origin "$current_branch"; then
        print_success "Git pull successful"
    else
        print_error "Git pull failed"
        exit 1
    fi

    # Reinstall
    print_info "Reinstalling package..."
    if [[ $INSTALL_TYPE == "dev" ]]; then
        if $USE_UV; then
            uv pip install -e ".[dev]"
        else
            python3 -m pip install -e ".[dev]"
        fi
    else
        if $USE_UV; then
            uv pip install .
        else
            python3 -m pip install .
        fi
    fi

    print_success "Updated from source"
}

# Get new version
get_new_version() {
    print_header "New Version"

    # Clear command cache
    hash -r 2>/dev/null || true

    local version=$(lazarus --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    echo -e "${BLUE}New version: ${GREEN}$version${NC}"

    NEW_VERSION=$version
}

# Run migrations (placeholder for future use)
run_migrations() {
    if $SKIP_MIGRATIONS; then
        print_info "Skipping migrations (--skip-migrations flag)"
        return 0
    fi

    print_header "Running Migrations"

    # Check if there are any migrations to run
    # This is a placeholder - actual migration logic would go here
    print_info "Checking for migrations..."

    # For now, just print a message
    print_info "No migrations required for this version"

    # Future migration examples:
    # - Config file format changes
    # - Database schema updates
    # - History file format updates
}

# Display changelog highlights
display_changelog() {
    print_header "Changelog Highlights"

    # Try to read changelog if available
    local changelog_file="$PROJECT_ROOT/CHANGELOG.md"

    if [[ -f "$changelog_file" ]] && [[ $INSTALL_TYPE != "pip" ]]; then
        print_info "Recent changes:\n"

        # Extract the most recent version section
        # Look for lines between ## [version] headers
        local in_section=false
        local line_count=0
        local max_lines=15

        while IFS= read -r line; do
            if [[ $line =~ ^##\  ]]; then
                if $in_section; then
                    break
                fi
                in_section=true
                echo -e "${GREEN}$line${NC}"
            elif $in_section; then
                echo "$line"
                ((line_count++))
                if [[ $line_count -ge $max_lines ]]; then
                    echo -e "\n${BLUE}... see CHANGELOG.md for more${NC}"
                    break
                fi
            fi
        done < "$changelog_file"

        echo ""
    else
        print_info "View full changelog at:"
        echo -e "${BLUE}https://github.com/yourusername/lazarus/blob/main/CHANGELOG.md${NC}"
        echo ""
    fi
}

# Verify update
verify_update() {
    print_header "Verifying Update"

    if ! command -v lazarus &> /dev/null; then
        print_error "lazarus command not found after update"
        exit 1
    fi

    # Check if version changed
    if [[ "$CURRENT_VERSION" != "unknown" ]] && [[ "$NEW_VERSION" != "unknown" ]]; then
        if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
            print_warning "Version unchanged - you may already have the latest version"
        else
            print_success "Successfully updated from $CURRENT_VERSION to $NEW_VERSION"
        fi
    else
        print_success "Update completed"
    fi
}

# Print next steps
print_next_steps() {
    print_header "Update Complete"

    cat << EOF
Lazarus has been updated successfully!

Next steps:

1. Verify the installation:
   ${GREEN}lazarus check${NC}

2. Review your configuration:
   ${GREEN}lazarus validate${NC}

3. Check for breaking changes in CHANGELOG.md

EOF

    if [[ $INSTALL_TYPE == "dev" ]]; then
        echo -e "${BLUE}Development mode:${NC}"
        echo -e "  - Run tests: ${GREEN}pytest${NC}"
        echo -e "  - Check types: ${GREEN}mypy src/lazarus${NC}"
        echo ""
    fi

    echo -e "Documentation: ${BLUE}https://github.com/yourusername/lazarus#readme${NC}"
    echo ""
}

# Main update flow
main() {
    echo -e "${BLUE}"
    cat << "EOF"
    __    _____  ____  _____  ____  __  __ _____
   / /   / _ \ \/ /\ \/ / _ \/ ___||  \/  / ____|
  / /   | |_| |  \  \  / |_| \  \  | |\/| |  _|
 / /    |  _  /  /  /  |  _  /  /  | |  | | |___
/_/     |_| |_/_/\_/\_/|_| |_/\_\  |_|  |_|_____|

Update Script

EOF
    echo -e "${NC}"

    # Check installation
    check_installation

    # Get current version
    get_current_version

    # Detect installation type
    detect_install_type

    # Confirm update
    confirm_update

    # Update based on installation type
    case $INSTALL_TYPE in
        pip)
            update_from_pip
            ;;
        source|dev)
            update_from_source
            ;;
    esac

    # Get new version
    get_new_version

    # Run migrations
    run_migrations

    # Verify update
    verify_update

    # Display changelog
    display_changelog

    # Print next steps
    print_next_steps
}

# Run main update flow
main
