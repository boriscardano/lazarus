#!/usr/bin/env bash

#######################################################################################
# Lazarus Workflow Setup Script
#
# This script helps set up GitHub Actions workflows for Lazarus automated healing.
# It copies workflow templates from the workflows/ directory to .github/workflows/
# and performs basic customization based on user input.
#
# Usage:
#   ./scripts/setup-workflows.sh [OPTIONS]
#
# Options:
#   --help                  Show this help message
#   --non-interactive       Run in non-interactive mode with defaults
#   --workflow TYPE         Specify workflow type (scheduled, on-failure, manual, all)
#   --schedule CRON         Set cron schedule (default: "0 */6 * * *")
#   --script-path PATH      Set script path to monitor (default: "./scripts/main.py")
#
#######################################################################################

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Default values
DEFAULT_SCHEDULE="0 */6 * * *"
DEFAULT_SCRIPT_PATH="./scripts/main.py"
NON_INTERACTIVE=false
SELECTED_WORKFLOW=""
CUSTOM_SCHEDULE=""
CUSTOM_SCRIPT_PATH=""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

#######################################################################################
# Helper Functions
#######################################################################################

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

show_help() {
    cat << EOF
Lazarus Workflow Setup Script

This script helps you set up GitHub Actions workflows for automated healing.

USAGE:
    ${0} [OPTIONS]

OPTIONS:
    --help                  Show this help message and exit
    --non-interactive       Run in non-interactive mode with default values
    --workflow TYPE         Specify workflow type to install
                           Types: scheduled, on-failure, manual, all
    --schedule CRON         Set cron schedule for scheduled workflow
                           Default: "${DEFAULT_SCHEDULE}"
    --script-path PATH      Set default script path to monitor
                           Default: "${DEFAULT_SCRIPT_PATH}"

EXAMPLES:
    # Interactive mode (prompts for all options)
    ${0}

    # Install all workflows non-interactively with defaults
    ${0} --non-interactive --workflow all

    # Install only scheduled workflow with custom schedule
    ${0} --workflow scheduled --schedule "0 */4 * * *"

    # Install manual workflow with custom script path
    ${0} --workflow manual --script-path "./src/app.py"

WORKFLOW TYPES:
    scheduled    - Runs healing on a schedule (e.g., every 6 hours)
    on-failure   - Reusable workflow for healing failed scripts
    manual       - Manually triggered workflow with full control
    all          - Install all workflow types

PREREQUISITES:
    - Git repository initialized
    - workflows/ directory with workflow templates
    - GitHub repository with Actions enabled

NOTES:
    - This script is idempotent and can be run multiple times safely
    - Existing workflows will be backed up before replacement
    - Remember to add ANTHROPIC_API_KEY to GitHub secrets after setup

EOF
}

#######################################################################################
# Validation Functions
#######################################################################################

check_git_repo() {
    print_info "Checking if running from a git repository..."

    if [ ! -d "${PROJECT_ROOT}/.git" ]; then
        print_error "Not a git repository!"
        print_error "Please initialize a git repository first:"
        echo ""
        echo "    cd ${PROJECT_ROOT}"
        echo "    git init"
        echo ""
        exit 1
    fi

    print_success "Running from a git repository"
}

check_workflows_dir() {
    print_info "Checking for workflow templates..."

    if [ ! -d "${PROJECT_ROOT}/workflows" ]; then
        print_error "workflows/ directory not found!"
        print_error "Expected location: ${PROJECT_ROOT}/workflows"
        exit 1
    fi

    # Count available workflow templates
    local template_count
    template_count=$(find "${PROJECT_ROOT}/workflows" -name "*.yaml" -o -name "*.yml" | wc -l)

    if [ "$template_count" -eq 0 ]; then
        print_error "No workflow templates found in workflows/ directory!"
        exit 1
    fi

    print_success "Found ${template_count} workflow template(s)"
}

ensure_github_workflows_dir() {
    print_info "Ensuring .github/workflows directory exists..."

    local workflows_dir="${PROJECT_ROOT}/.github/workflows"

    if [ ! -d "${workflows_dir}" ]; then
        mkdir -p "${workflows_dir}"
        print_success "Created .github/workflows directory"
    else
        print_success ".github/workflows directory already exists"
    fi
}

validate_cron_schedule() {
    local schedule="$1"

    # Basic validation: 5 fields separated by spaces
    local field_count
    field_count=$(echo "${schedule}" | awk '{print NF}')

    if [ "${field_count}" -ne 5 ]; then
        print_error "Invalid cron schedule: ${schedule}"
        print_error "Expected format: 'minute hour day month weekday'"
        return 1
    fi

    return 0
}

#######################################################################################
# User Input Functions
#######################################################################################

prompt_workflow_type() {
    if [ -n "${SELECTED_WORKFLOW}" ]; then
        echo "${SELECTED_WORKFLOW}"
        return
    fi

    echo ""
    echo "Which workflows would you like to install?"
    echo ""
    echo "  1) scheduled   - Run healing on a schedule (e.g., every 6 hours)"
    echo "  2) on-failure  - Reusable workflow for healing failed scripts"
    echo "  3) manual      - Manually triggered workflow with full control"
    echo "  4) all         - Install all workflow types"
    echo ""

    while true; do
        read -rp "Enter your choice [1-4]: " choice

        case $choice in
            1) echo "scheduled"; return ;;
            2) echo "on-failure"; return ;;
            3) echo "manual"; return ;;
            4) echo "all"; return ;;
            *) print_error "Invalid choice. Please enter 1-4." ;;
        esac
    done
}

prompt_cron_schedule() {
    if [ -n "${CUSTOM_SCHEDULE}" ]; then
        echo "${CUSTOM_SCHEDULE}"
        return
    fi

    echo ""
    print_info "Configure scheduled workflow cron schedule"
    echo ""
    echo "Examples:"
    echo "  0 */6 * * *  - Every 6 hours"
    echo "  0 */4 * * *  - Every 4 hours"
    echo "  0 0 * * *    - Daily at midnight"
    echo "  0 */12 * * * - Twice daily"
    echo ""

    while true; do
        read -rp "Enter cron schedule [${DEFAULT_SCHEDULE}]: " schedule

        # Use default if empty
        schedule="${schedule:-${DEFAULT_SCHEDULE}}"

        if validate_cron_schedule "${schedule}"; then
            echo "${schedule}"
            return
        fi
    done
}

prompt_script_path() {
    if [ -n "${CUSTOM_SCRIPT_PATH}" ]; then
        echo "${CUSTOM_SCRIPT_PATH}"
        return
    fi

    echo ""
    read -rp "Enter default script path to monitor [${DEFAULT_SCRIPT_PATH}]: " script_path

    # Use default if empty
    script_path="${script_path:-${DEFAULT_SCRIPT_PATH}}"

    echo "${script_path}"
}

#######################################################################################
# Workflow Installation Functions
#######################################################################################

backup_existing_workflow() {
    local workflow_file="$1"
    local backup_file="${workflow_file}.backup.$(date +%Y%m%d-%H%M%S)"

    if [ -f "${workflow_file}" ]; then
        cp "${workflow_file}" "${backup_file}"
        print_warning "Backed up existing workflow to: $(basename "${backup_file}")"
    fi
}

install_workflow() {
    local workflow_type="$1"
    local schedule="$2"
    local script_path="$3"

    local source_file="${PROJECT_ROOT}/workflows/lazarus-${workflow_type}.yaml"
    local dest_file="${PROJECT_ROOT}/.github/workflows/lazarus-${workflow_type}.yaml"

    # Check if source template exists
    if [ ! -f "${source_file}" ]; then
        print_error "Template not found: ${source_file}"
        return 1
    fi

    print_info "Installing ${workflow_type} workflow..."

    # Backup existing workflow if it exists
    backup_existing_workflow "${dest_file}"

    # Copy template
    cp "${source_file}" "${dest_file}"

    # Perform string replacements
    if [ "${workflow_type}" = "scheduled" ]; then
        # Replace cron schedule
        sed -i.tmp "s|0 \*/6 \* \* \*|${schedule}|g" "${dest_file}"
        rm -f "${dest_file}.tmp"
    fi

    # Replace script path placeholders (if any exist in templates)
    if grep -q "PLACEHOLDER_SCRIPT_PATH" "${dest_file}" 2>/dev/null; then
        sed -i.tmp "s|PLACEHOLDER_SCRIPT_PATH|${script_path}|g" "${dest_file}"
        rm -f "${dest_file}.tmp"
    fi

    print_success "Installed: .github/workflows/lazarus-${workflow_type}.yaml"

    return 0
}

#######################################################################################
# Summary and Reminders
#######################################################################################

show_summary() {
    local workflow_type="$1"
    local schedule="$2"
    local script_path="$3"

    print_header "Installation Summary"

    echo "Workflow(s) installed:"
    echo ""

    if [ "${workflow_type}" = "all" ]; then
        echo "  • Scheduled workflow (runs on schedule)"
        echo "  • On-failure workflow (reusable for failed scripts)"
        echo "  • Manual workflow (on-demand healing)"
    else
        echo "  • ${workflow_type} workflow"
    fi

    echo ""
    echo "Configuration:"
    echo "  • Cron schedule:   ${schedule}"
    echo "  • Default script:  ${script_path}"
    echo ""

    print_success "Workflow installation complete!"
}

show_next_steps() {
    print_header "Next Steps"

    echo "To complete the setup, you need to:"
    echo ""

    print_info "1. Add ANTHROPIC_API_KEY to GitHub Secrets"
    echo ""
    echo "   a. Go to your repository on GitHub"
    echo "   b. Navigate to Settings → Secrets and variables → Actions"
    echo "   c. Click 'New repository secret'"
    echo "   d. Name: ANTHROPIC_API_KEY"
    echo "   e. Value: Your Anthropic API key"
    echo "   f. Click 'Add secret'"
    echo ""

    print_info "2. (Optional) Set up GitHub Token"
    echo ""
    echo "   For enhanced permissions (create PRs, issues), add GH_TOKEN:"
    echo "   a. Create a Personal Access Token (PAT) on GitHub"
    echo "   b. Permissions needed: repo, workflow"
    echo "   c. Add as repository secret: GH_TOKEN"
    echo ""

    print_info "3. Configure Runner (if using self-hosted)"
    echo ""
    echo "   The workflows are configured to use 'self-hosted' runners by default."
    echo "   If you don't have a self-hosted runner:"
    echo ""
    echo "   Option A: Set up a self-hosted runner"
    echo "     - See: runner-setup/README.md"
    echo "     - Run: cd runner-setup && ./setup-runner.sh"
    echo ""
    echo "   Option B: Use GitHub-hosted runners"
    echo "     - Edit the workflow files in .github/workflows/"
    echo "     - Change 'runs-on: self-hosted' to 'runs-on: ubuntu-latest'"
    echo ""

    print_info "4. Test the Workflows"
    echo ""
    echo "   • Go to Actions tab in your GitHub repository"
    echo "   • Select 'Lazarus Manual Healing' workflow"
    echo "   • Click 'Run workflow' to test"
    echo ""

    print_info "5. Review and Commit"
    echo ""
    echo "   git add .github/workflows/"
    echo "   git commit -m 'Add Lazarus healing workflows'"
    echo "   git push"
    echo ""

    print_warning "Security Reminder"
    echo ""
    echo "  • Never commit API keys or secrets to the repository"
    echo "  • Use GitHub Secrets for all sensitive values"
    echo "  • Review workflow permissions before enabling"
    echo "  • Consider using environment-specific secrets"
    echo ""
}

show_workflow_details() {
    print_header "Installed Workflow Details"

    echo "📅 Scheduled Workflow (lazarus-scheduled.yaml)"
    echo "   • Runs automatically on a cron schedule"
    echo "   • Can be manually triggered via workflow_dispatch"
    echo "   • Creates PRs for successful fixes"
    echo "   • Creates issues on failure"
    echo ""

    echo "🔧 On-Failure Workflow (lazarus-on-failure.yaml)"
    echo "   • Reusable workflow for other GitHub Actions"
    echo "   • Call from other workflows when scripts fail"
    echo "   • Customizable parameters (timeout, attempts, etc.)"
    echo "   • Returns healing results as outputs"
    echo ""

    echo "🎯 Manual Workflow (lazarus-manual.yaml)"
    echo "   • On-demand healing via GitHub Actions UI"
    echo "   • Full control over all parameters"
    echo "   • Input validation before healing"
    echo "   • Detailed reporting and summaries"
    echo ""
}

#######################################################################################
# Main Script
#######################################################################################

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --workflow)
                SELECTED_WORKFLOW="$2"
                shift 2
                ;;
            --schedule)
                CUSTOM_SCHEDULE="$2"
                shift 2
                ;;
            --script-path)
                CUSTOM_SCRIPT_PATH="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                echo ""
                echo "Run '${0} --help' for usage information."
                exit 1
                ;;
        esac
    done
}

main() {
    parse_arguments "$@"

    print_header "Lazarus Workflow Setup"

    # Step 1: Validate prerequisites
    check_git_repo
    check_workflows_dir
    ensure_github_workflows_dir

    # Step 2: Get user input (or use defaults in non-interactive mode)
    local workflow_type
    local schedule
    local script_path

    if [ "${NON_INTERACTIVE}" = true ]; then
        workflow_type="${SELECTED_WORKFLOW:-all}"
        schedule="${CUSTOM_SCHEDULE:-${DEFAULT_SCHEDULE}}"
        script_path="${CUSTOM_SCRIPT_PATH:-${DEFAULT_SCRIPT_PATH}}"

        print_info "Running in non-interactive mode"
        print_info "Workflow type: ${workflow_type}"
        print_info "Schedule: ${schedule}"
        print_info "Script path: ${script_path}"
    else
        workflow_type=$(prompt_workflow_type)
        schedule=$(prompt_cron_schedule)
        script_path=$(prompt_script_path)
    fi

    # Validate cron schedule
    if ! validate_cron_schedule "${schedule}"; then
        exit 1
    fi

    echo ""
    print_header "Installing Workflows"

    # Step 3: Install selected workflow(s)
    if [ "${workflow_type}" = "all" ]; then
        install_workflow "scheduled" "${schedule}" "${script_path}"
        install_workflow "on-failure" "${schedule}" "${script_path}"
        install_workflow "manual" "${schedule}" "${script_path}"
    else
        install_workflow "${workflow_type}" "${schedule}" "${script_path}"
    fi

    # Step 4: Show summary and next steps
    echo ""
    show_summary "${workflow_type}" "${schedule}" "${script_path}"
    echo ""
    show_workflow_details
    show_next_steps

    print_success "Setup complete! Follow the next steps above to finish configuration."
}

# Run main function with all arguments
main "$@"
