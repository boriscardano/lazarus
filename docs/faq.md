# Frequently Asked Questions

Common questions about Lazarus.

## Table of Contents

- [General Questions](#general-questions)
- [Usage Questions](#usage-questions)
- [Configuration Questions](#configuration-questions)
- [Integration Questions](#integration-questions)
- [Troubleshooting Questions](#troubleshooting-questions)
- [Security Questions](#security-questions)

---

## General Questions

### What is Lazarus?

Lazarus is a self-healing script runner that automatically detects failing scripts, analyzes errors using Claude Code AI, generates fixes, and creates pull requests. It transforms manual debugging into an automated workflow.

**Key capabilities:**
- Detects script failures (exit codes, exceptions, timeouts)
- Collects comprehensive error context
- Uses Claude Code to diagnose and fix issues
- Automatically verifies fixes by re-running scripts
- Creates pull requests with the proposed changes
- Sends notifications about results

### Why use Lazarus instead of calling Claude Code directly?

Lazarus adds essential orchestration on top of Claude Code:

1. **Error Detection** - Automatically identifies when scripts fail
2. **Context Collection** - Gathers stdout, stderr, git history, system info
3. **Verification** - Re-runs scripts to confirm fixes work
4. **PR Automation** - Creates well-formatted pull requests automatically
5. **Notification** - Alerts you across Slack, Discord, Email, GitHub
6. **Secrets Safety** - Redacts sensitive data before sending to AI
7. **Retry Logic** - Configurable attempt limits and timeouts
8. **CI/CD Integration** - Runs on schedule or on failure events

### What are the system requirements?

**Minimum Requirements:**
- Python 3.11 or higher
- Git (with `user.name` and `user.email` configured)
- Claude Code CLI (installed and authenticated)
- GitHub CLI `gh` (for PR creation)

**For Self-Hosted Runners:**
- macOS 11+ or Ubuntu 20.04+ / Debian 11+ / RHEL 8+
- 4GB RAM (8GB recommended)
- 20GB+ free disk space

**For Notifications:**
- Slack Webhook URL (optional, for Slack notifications)
- Discord Webhook URL (optional, for Discord notifications)
- GitHub token (included in `gh` CLI authentication)

### Is Lazarus free to use?

Lazarus itself is open source and free. However, using Claude Code to generate fixes incurs costs based on the Anthropic API pricing. You need an Anthropic API key with available credits.

See [Getting Started](getting-started.md) for installation steps.

### How does Lazarus compare to other automation tools?

Lazarus is specifically designed for automated script healing with AI. Unlike general CI/CD tools:

| Feature | Lazarus | GitHub Actions | Other Tools |
|---------|---------|---|---|
| Automatic error detection | ✅ | Manual | ⚠️ Varies |
| AI-powered diagnosis | ✅ | ❌ | ❌ |
| Auto-generate fixes | ✅ | ❌ | ❌ |
| PR creation | ✅ | Manual | ⚠️ |
| Notifications | ✅ | Basic | ⚠️ |
| Secret handling | ✅ | ✅ | ⚠️ |
| Self-hosted runners | ✅ | ✅ | ⚠️ |

Lazarus complements CI/CD tools - you typically run it within a workflow on self-hosted runners.

---

## Usage Questions

### How do I get started with Lazarus?

Follow the [Getting Started Guide](./getting-started.md) for installation and your first healing:

```bash
# 1. Install
uv pip install lazarus-heal

# 2. Check prerequisites
lazarus check

# 3. Initialize config
lazarus init

# 4. Run on a script
lazarus run ./scripts/your_script.py

# 5. Review the generated PR
gh pr list
```

Complete walkthrough with examples takes about 15 minutes.

### Can I run multiple scripts in parallel?

Lazarus runs scripts sequentially by default. However:

1. **In CI/CD workflows** - Use parallel GitHub Actions jobs
2. **With multiple scripts** - Create separate Lazarus jobs
3. **Concurrent healing** - Lazarus can heal multiple failing scripts if configured

Example GitHub Actions parallel workflow:
```yaml
jobs:
  heal-script-1:
    runs-on: self-hosted
    steps:
      - run: lazarus run ./scripts/script1.py

  heal-script-2:
    runs-on: self-hosted
    steps:
      - run: lazarus run ./scripts/script2.py
```

### How do I retry failed tasks?

Lazarus automatically retries based on configuration:

```yaml
healing:
  max_attempts: 3  # Try up to 3 times
  timeout_per_attempt: 120  # 2 minutes per attempt
```

Manual retry:
```bash
# Re-run the same healing command
lazarus run ./scripts/your_script.py
```

View history of attempts:
```bash
lazarus history
```

### Can I use Lazarus in CI/CD?

Yes! Lazarus is designed for CI/CD integration:

**GitHub Actions:** See [GitHub Actions Integration](github-actions.md)
```yaml
name: Auto-Heal Failing Scripts
on:
  schedule:
    - cron: "0 2 * * *"  # Daily at 2 AM

jobs:
  heal:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v3
      - run: lazarus run ./scripts/*.py
```

**Self-Hosted Runners:** See [Runner Setup Guide](self-hosted-runner.md)

### How do I preview changes before creating a PR?

Use dry-run mode (if available in your version):

```bash
# Run healing without creating PR
lazarus run ./script.py --no-pr
```

Or disable PR creation in config:
```yaml
git:
  create_pr: false  # Healing happens, but no PR
```

Review the changes:
```bash
git diff  # See what changed
git status  # Check modified files
```

Enable PR creation when ready:
```yaml
git:
  create_pr: true
```

---

## Configuration Questions

### Where should I put my lazarus.yaml file?

Put `lazarus.yaml` in your project root (same directory as `.git/`):

```
my-project/
├── .git/
├── scripts/
│   └── my_script.py
├── src/
└── lazarus.yaml  ← Here
```

Lazarus searches for the config in this order:
1. Current working directory
2. Parent directories (up to repository root)
3. Home directory

Create a template:
```bash
lazarus init  # Generates lazarus.yaml
```

### How do I specify which files Claude should modify?

Use `allowed_files` in the healing configuration:

```yaml
healing:
  allowed_files:
    - "scripts/*.py"           # Glob patterns
    - "utils/helpers.py"       # Specific files
    - "src/**/*.js"            # Recursive patterns
    - "README.md"              # Documentation
```

**Important:** Files outside `allowed_files` won't be modified, even if needed. Include all potentially fixable files.

Example for multi-file fixes:
```yaml
healing:
  allowed_files:
    - "main.py"
    - "utils/**/*.py"
    - "lib/**/*.py"
```

### Can I use environment variables in my configuration?

Yes, use `${VAR_NAME}` syntax:

```yaml
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"

scripts:
  - name: "backup"
    path: "${SCRIPT_DIR}/backup.sh"
```

Define variables:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export SCRIPT_DIR="/path/to/scripts"

lazarus run ./script.py
```

Or in `.env` file (loaded automatically):
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SCRIPT_DIR=/path/to/scripts
```

### How do I configure healing parameters?

Control healing behavior with these settings:

```yaml
healing:
  max_attempts: 3              # Maximum healing attempts
  timeout_per_attempt: 300     # Seconds per attempt
  total_timeout: 900           # Total time limit
  allowed_files:               # Files Claude can modify
    - "src/**/*.py"
  skip_verification: false     # Always verify fixes
```

Fine-tune for your needs:
- **Fast feedback:** `max_attempts: 2, timeout_per_attempt: 120`
- **Thorough healing:** `max_attempts: 5, timeout_per_attempt: 300`
- **Complex scripts:** `total_timeout: 1800` (30 minutes)

### What verification types are supported?

Lazarus verifies by re-running the script and checking:

1. **Exit Code** - Script must exit with code 0 (success)
2. **Stdout/Stderr** - Output can be compared or checked
3. **Output File** - Generated files can be verified
4. **Custom Command** - Run any shell command to verify

Example:
```yaml
healing:
  skip_verification: false     # Always verify

# Verification happens automatically by re-running the script
# If exit code is 0, fix is considered successful
```

For custom verification:
```bash
# After healing, manually verify
lazarus run ./script.py
# Lazarus re-runs the script to confirm fix works
```

---

## Integration Questions

### Does Lazarus work with my CI/CD system?

Lazarus integrates with:

**Primary Integration:**
- **GitHub Actions** ✅ - Full support with self-hosted runners
  - See [GitHub Actions Guide](github-actions.md)
  - Works with scheduled workflows
  - Supports workflow dispatches

**Supported CI/CD Platforms (via GitHub Actions):**
- Jenkins - via GitHub webhooks
- GitLab CI - convert to Actions or use runner
- CircleCI - with custom integration
- GitOps tools - manual trigger or webhooks

**Prerequisites for CI/CD:**
1. Self-hosted runner with Lazarus installed
2. Anthropic API key configured
3. GitHub token for PR creation
4. Git user configured

See [Self-Hosted Runner Setup](self-hosted-runner.md) for detailed installation.

### Can I use Lazarus with GitLab/Bitbucket?

**Current Status:**
- **GitHub:** ✅ Full support
- **GitLab:** ⚠️ Partial (works via GH CLI with mirror)
- **Bitbucket:** ⚠️ Partial (works via GH CLI with mirror)

**For GitLab/Bitbucket:**
1. Mirror repository to GitHub
2. Run Lazarus on GitHub mirror
3. Sync changes back

Or contribute support for your platform on GitHub.

### How does Lazarus authenticate with GitHub?

Lazarus uses GitHub CLI (`gh`) authentication:

**Setup:**
```bash
# Authenticate with GitHub
gh auth login

# Choose: HTTPS, SSH, or GitHub token
# Verify authentication
gh auth status
```

**Authentication Flow:**
1. `gh` CLI reads stored token from `~/.config/gh/hosts.yml`
2. Lazarus uses `gh` for PR creation and status checks
3. Token needs `repo` scope for private repos, `public_repo` for public

**For CI/CD (GitHub Actions):**
```yaml
jobs:
  heal:
    runs-on: self-hosted
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Can I use a different AI model instead of Claude?

Currently, **only Claude Code is supported**. Lazarus is built specifically around the Claude Code CLI.

**Future possibilities:**
- OpenAI Code Interpreter
- Anthropic other models (if they add code execution)
- Other AI providers (community contribution)

For now, you need the Claude Code CLI and a valid Anthropic API key.

### Does Lazarus support monorepos?

Yes, with careful configuration:

```yaml
scripts:
  # Service 1
  - name: "service-1-test"
    path: "./services/service1/test.py"

  # Service 2
  - name: "service-2-sync"
    path: "./services/service2/sync.sh"

healing:
  allowed_files:
    - "services/service1/**/*.py"
    - "services/service2/**/*.sh"
    - "shared/**/*.py"  # Shared utilities
```

**Monorepo Best Practices:**
1. Use separate `lazarus.yaml` per service in subdirectories
2. Reference files relative to config location
3. Use glob patterns for cross-service fixes
4. Configure separate branch prefixes if needed

```yaml
git:
  branch_prefix: "lazarus/service1/fix"  # Per-service branches
```

---

## Troubleshooting Questions

### Why isn't Claude making the changes I requested?

Common causes and solutions:

**1. Files not in allowed_files:**
```yaml
# Wrong - file not listed
healing:
  allowed_files:
    - "script.py"

# Right - include the file
healing:
  allowed_files:
    - "script.py"
    - "lib/helpers.py"  # Add missing file
```

**2. Error message too complex:**
Claude works best with clear, isolated errors. If errors are tangled:
- Fix simpler errors first
- Split complex scripts
- Provide context in allowed files

**3. Task beyond Claude's scope:**
Some issues need human judgment:
- Architectural changes
- Business logic decisions
- Complex refactoring

**4. API key issues:**
```bash
# Verify authentication
claude auth status

# Re-authenticate if needed
claude auth login
```

**Solution:**
1. Review error logs: `lazarus history`
2. Check allowed files: `cat lazarus.yaml`
3. Try with simpler script first
4. Increase max_attempts for complex issues

### My verification keeps failing, what should I do?

Verification fails when script still exits with error after fix attempt.

**Debug steps:**
```bash
# 1. Run script directly (before Lazarus)
python3 script.py
# Note the error

# 2. Check Lazarus logs
lazarus history

# 3. Try with more attempts
lazarus run ./script.py --max-attempts 5

# 4. Increase timeout
# Edit lazarus.yaml:
healing:
  timeout_per_attempt: 300
```

**Common causes:**
- Fix incomplete (Claude needs more context)
- Dependencies missing (pip, npm packages)
- External resources unavailable
- Insufficient allowed_files configured

**Solution:**
1. Add more files to `allowed_files`
2. Provide more context in error output
3. Check dependencies are installed
4. Verify external resources are accessible

### How do I see what Claude is doing?

Check logs and history:

```bash
# View healing attempts
lazarus history

# View detailed logs
lazarus run ./script.py --verbose

# Check git diffs
git diff HEAD  # Changes made by last healing

# Review generated PR
gh pr view

# Check Claude's reasoning in PR description
```

**For debugging:**
```bash
# Run with verbose output
lazarus run ./script.py -v

# Check what context was sent
lazarus run ./script.py --debug  # Dumps context to file

# Monitor live
tail -f ~/.lazarus/logs/latest.log
```

### Why did my task timeout?

Timeouts occur when healing takes too long:

**Causes:**
- Script execution is slow
- Claude Code response is slow
- Network issues
- Complex problem requiring multiple attempts

**Solutions:**
```yaml
healing:
  timeout_per_attempt: 300   # Increase from 120
  total_timeout: 1800        # Increase total limit
  max_attempts: 5            # More time to solve
```

For long-running scripts:
```bash
# Increase limits for this run
lazarus run ./slow_script.py --timeout 600
```

### How do I cancel a running task?

**While running:**
```bash
# Press Ctrl+C in terminal
# Lazarus will exit gracefully
```

**Check running processes:**
```bash
ps aux | grep lazarus
ps aux | grep claude

# Kill if stuck
pkill -f lazarus
pkill -f claude
```

**In CI/CD:**
```yaml
# Add timeout to GitHub Actions job
jobs:
  heal:
    runs-on: self-hosted
    timeout-minutes: 30  # Max 30 minutes
    steps:
      - run: lazarus run ./script.py
```

**Check status:**
```bash
lazarus history  # See if last run completed
```

---

## Security Questions

### Is it safe to give AI access to my code?

Yes, but with precautions:

**What gets sent to Claude:**
- Script content (to fix)
- Error messages (for context)
- Git history (limited)
- System information (basic)
- Output samples (for debugging)

**What does NOT get sent:**
- Secrets or credentials (automatically redacted)
- Private keys
- API keys
- Environment variables
- Database credentials

**Security best practices:**
1. **Review code sent** - Check what's included in healing context
2. **Use allowed_files** - Limit which files can be modified
3. **Keep secrets out** - Never hardcode secrets in code
4. **Use .env files** - Store secrets separately
5. **Review PRs** - Always review AI-generated fixes before merging

**Risk Assessment:**
- ✅ Safe: Sending error messages and code structure
- ✅ Safe: Using Claude Code for debugging
- ⚠️ Risky: Hardcoded credentials in scripts
- ❌ Unsafe: Sending secrets in comments or test data

### How does Lazarus handle secrets?

Lazarus automatically redacts sensitive information:

**Automatically Redacted:**
- API keys matching common patterns
- AWS/GCP credentials
- Database passwords
- Private keys
- Authentication tokens
- Passwords in connection strings

**Example:**
```python
# Your script
API_KEY = "sk-1234567890abcdef"

# What Claude sees
API_KEY = "[REDACTED_API_KEY]"
```

**For custom secrets:**
```yaml
# Configure patterns to redact
security:
  redact_patterns:
    - "SECRET_.*"
    - ".*_PASSWORD"
    - "TOKEN"
```

**Best practices:**
1. Store secrets in environment variables
2. Load from .env files
3. Use `export VAR=value` at runtime
4. Never commit secrets to git
5. Enable Lazarus redaction

See [Security Documentation](./security.md) for detailed information.

### What permissions does Lazarus need?

**File System:**
- Read access to script files
- Read access to allowed files for context
- Write access to allowed files (for fixes)
- Write access to `.git/` for commits

**Network:**
- Outbound HTTPS to api.anthropic.com
- Outbound HTTPS to github.com
- Outbound HTTPS to notification services (Slack, Discord, etc.)

**Git:**
- Ability to create branches
- Ability to commit changes
- Ability to create pull requests (via `gh` CLI)

**Recommended setup:**
```bash
# Create separate user for Lazarus (optional)
useradd -m lazarus-runner

# Grant minimum permissions
chmod 755 /path/to/scripts  # Read
chmod 755 /path/to/project  # Navigate

# Git access via SSH key
ssh-keygen -t ed25519 -C "lazarus@example.com"
# Add to GitHub as deploy key with PR permissions
```

### Can Lazarus accidentally commit secrets?

**No, with proper setup:**

1. **Secret redaction** - Secrets are redacted before sending to Claude
2. **Code review** - You review PRs before merging
3. **Limited scope** - Only allowed_files can be modified
4. **Git hooks** - Can add pre-commit hooks to prevent secrets

**Additional protection:**
```bash
# Install secret scanning pre-commit hook
pip install detect-secrets

# Initialize for your repo
detect-secrets scan > .secrets.baseline

# Check will prevent commits with secrets
pre-commit install  # With detect-secrets hook
```

**For CI/CD:**
```yaml
# GitHub Actions secret scanning
- name: Scan for secrets
  run: |
    pip install detect-secrets
    detect-secrets scan --baseline .secrets.baseline
```

### Should I review PRs created by Lazarus?

**Yes, always review PRs created by Lazarus before merging.**

Lazarus is a powerful tool, but AI-generated code should never be merged blindly:

**Review checklist:**
- [ ] Does the fix address the root cause?
- [ ] Is the code logic correct?
- [ ] Are there any side effects?
- [ ] Does it follow your coding standards?
- [ ] Are error cases handled?
- [ ] Does it match your project's patterns?
- [ ] Would you write it this way?

**Example PR review:**
1. Open the PR: `gh pr view`
2. Check the description for Claude's explanation
3. Review the diff for the actual changes
4. Run tests locally: `pytest tests/`
5. Test manually if needed
6. Comment with feedback if needed
7. Merge when confident

**When to reject:**
- ❌ Doesn't actually fix the problem
- ❌ Introduces security issues
- ❌ Breaks other functionality
- ❌ Uses deprecated patterns
- ❌ Poor code quality

**When to accept:**
- ✅ Solves the problem cleanly
- ✅ Follows project standards
- ✅ Tests pass
- ✅ Well-structured code
- ✅ No security concerns

### How do I report a security issue?

**For security vulnerabilities in Lazarus:**

1. **Do NOT open a public issue**
2. Email: security@lazarus-heal.dev (or check GitHub repository)
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

**For security issues in generated code:**
- Review the PR carefully before merging
- Use code review processes
- Run security scanners
- Test thoroughly

**Security best practices reminder:**
- Keep Lazarus updated
- Keep Claude Code CLI updated
- Keep Python updated
- Rotate API keys regularly
- Use strong authentication
- Monitor access logs
