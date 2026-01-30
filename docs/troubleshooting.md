# Troubleshooting

Common issues and solutions when using Lazarus.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Errors](#configuration-errors)
- [Claude Code Problems](#claude-code-problems)
- [Authentication Issues](#authentication-issues)
- [Git Problems](#git-problems)
- [PR Creation Issues](#pr-creation-issues)
- [Script Execution Failures](#script-execution-failures)
- [Performance Issues](#performance-issues)
- [Rate Limits](#rate-limits)
- [Getting Help](#getting-help)

---

## Installation Issues

### Problem: `command not found: lazarus`

**Cause**: Lazarus is not installed or not in PATH.

**Solution**:

```bash
# Verify installation
pip show lazarus-heal

# If not installed:
pip install lazarus-heal

# If installed but not in PATH, try:
python -m lazarus --help

# Or reinstall with pipx:
pipx install lazarus-heal
```

### Problem: ImportError or ModuleNotFoundError

**Cause**: Missing dependencies or corrupted installation.

**Solution**:

```bash
# Reinstall with dependencies
pip uninstall lazarus-heal
pip install --force-reinstall lazarus-heal

# Or install from source:
git clone https://github.com/yourusername/lazarus.git
cd lazarus
pip install -e .
```

### Problem: Python version incompatibility

**Cause**: Lazarus requires Python 3.11+.

**Solution**:

```bash
# Check Python version
python --version

# If < 3.11, upgrade Python:
# macOS with Homebrew
brew install python@3.12

# Linux with pyenv
pyenv install 3.12.0
pyenv global 3.12.0

# Or use pyenv to manage versions
```

### Problem: Permission denied when installing

**Cause**: Insufficient permissions for system-wide installation.

**Solution**:

```bash
# Install for user only (recommended):
pip install --user lazarus-heal

# Or use a virtual environment:
python -m venv venv
source venv/bin/activate
pip install lazarus-heal

# Or use pipx:
pipx install lazarus-heal
```

---

## Configuration Errors

### Problem: "Configuration file not found"

**Cause**: No `lazarus.yaml` in current directory or parents.

**Solution**:

```bash
# Create configuration template:
lazarus init

# Or specify config path:
lazarus heal script.py --config /path/to/lazarus.yaml

# Or check search locations:
# 1. Current directory
# 2. Parent directories up to git root
pwd
git rev-parse --show-toplevel
```

### Problem: "Invalid configuration: ..."

**Cause**: YAML syntax error or schema validation failure.

**Solution**:

```bash
# Validate configuration:
lazarus validate

# Common issues:
# 1. Incorrect indentation (use spaces, not tabs)
# 2. Missing required fields (name, path for scripts)
# 3. Invalid values (e.g., timeout out of range)

# Example of correct indentation:
scripts:
  - name: my-script    # 2 spaces
    path: scripts/test.py    # 4 spaces
```

### Problem: "Duplicate script names found"

**Cause**: Multiple scripts configured with the same name.

**Solution**:

```yaml
# Make sure all script names are unique:
scripts:
  - name: backup-prod    # Unique
    path: scripts/backup.py
  - name: backup-staging    # Different from above
    path: scripts/backup_staging.py
```

### Problem: "Invalid regex pattern"

**Cause**: Malformed regex in security redaction patterns.

**Solution**:

```yaml
# Test regex patterns separately:
import re
pattern = r"(?i)(api[_-]?key)[\s=:]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?"
re.compile(pattern)  # Should not raise error

# Common issues:
# - Unescaped special characters
# - Unclosed groups
# - Invalid escape sequences

# Use raw strings (r"...") for regex patterns
```

### Problem: Environment variable not substituted

**Cause**: Variable not set or incorrect syntax.

**Solution**:

```bash
# Check if variable is set:
echo $SLACK_WEBHOOK_URL

# Set variable:
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."

# Verify in config:
cat lazarus.yaml | grep SLACK_WEBHOOK_URL

# Correct syntax:
webhook_url: "${SLACK_WEBHOOK_URL}"    # Correct
webhook_url: "$SLACK_WEBHOOK_URL"      # Also correct
webhook_url: "SLACK_WEBHOOK_URL"       # Wrong - literal string
```

---

## Claude Code Problems

### Problem: "Claude Code CLI is not available"

**Cause**: Claude Code is not installed or not in PATH.

**Solution**:

```bash
# Check if Claude Code is installed:
which claude
claude --version

# If not installed:
npm install -g @anthropic-ai/claude-code

# If installed but not in PATH:
# Find installation location:
npm root -g

# Add to PATH in ~/.bashrc or ~/.zshrc:
export PATH="$PATH:$(npm root -g)/.bin"
source ~/.bashrc  # or ~/.zshrc
```

### Problem: "Claude Code timed out after X seconds"

**Cause**: Claude Code taking longer than configured timeout.

**Solution**:

```bash
# Increase timeout in configuration:
# lazarus.yaml
healing:
  timeout_per_attempt: 600  # 10 minutes instead of 5
  total_timeout: 1800       # 30 minutes total

# Or via command line:
lazarus heal script.py --timeout 1800
```

### Problem: Claude Code returns error

**Cause**: Various Claude Code issues (authentication, rate limits, bugs).

**Solution**:

```bash
# Enable verbose output:
lazarus heal script.py --verbose

# Check Claude Code directly:
claude -p "Test prompt"

# Re-authenticate Claude Code:
claude logout
claude login

# Check API key:
echo $ANTHROPIC_API_KEY

# Set API key if missing:
export ANTHROPIC_API_KEY="your-key-here"
```

### Problem: "No changes made" by Claude

**Cause**: Claude couldn't understand the error or fix it.

**Solutions**:

1. **Add custom prompt with more context**:

```yaml
scripts:
  - name: my-script
    path: scripts/test.py
    custom_prompt: |
      This script connects to PostgreSQL database.
      Use psycopg2 library for database operations.
      Configuration is in config/db.yaml.
```

2. **Check script has clear error messages**:

```python
# Good - clear error
raise ValueError(f"Invalid config: missing 'database_url'")

# Bad - unclear error
raise Exception("Error")
```

3. **Ensure error is reproducible**:

```bash
# Test script directly:
./scripts/test.py
echo $?  # Should be non-zero for failure
```

---

## Authentication Issues

### Problem: "Authentication required" for Claude

**Cause**: Claude Code not authenticated.

**Solution**:

```bash
# Authenticate Claude Code:
claude login

# Or set API key directly:
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify authentication:
claude -p "test"
```

### Problem: "Authentication required" for GitHub

**Cause**: GitHub CLI not authenticated.

**Solution**:

```bash
# Authenticate GitHub CLI:
gh auth login

# Follow prompts to authenticate via browser or token

# Verify authentication:
gh auth status

# If using token:
gh auth login --with-token < token.txt

# Or set token:
export GH_TOKEN="ghp_..."
```

### Problem: "Insufficient permissions" for GitHub

**Cause**: GitHub token lacks required scopes.

**Solution**:

```bash
# Required scopes for Lazarus:
# - repo (full repository access)
# - workflow (if using GitHub Actions)

# Re-authenticate with correct scopes:
gh auth refresh -s repo,workflow

# Or create new token at:
# https://github.com/settings/tokens
# With scopes: repo, workflow

# Then authenticate:
gh auth login --with-token
```

---

## Git Problems

### Problem: "not a git repository"

**Cause**: Lazarus must run inside a git repository.

**Solution**:

```bash
# Initialize git repository:
git init
git add .
git commit -m "Initial commit"

# Or run Lazarus from repository root:
cd /path/to/your/repo
lazarus heal scripts/test.py
```

### Problem: "working tree is dirty"

**Cause**: Uncommitted changes exist (this is just a warning).

**Solution**:

```bash
# Lazarus will still run, but consider:

# Option 1: Commit changes:
git add .
git commit -m "Work in progress"

# Option 2: Stash changes:
git stash
lazarus heal scripts/test.py
git stash pop

# Option 3: Continue anyway (safe):
# Lazarus creates new branches and won't overwrite
```

### Problem: "detached HEAD state"

**Cause**: Not on a branch.

**Solution**:

```bash
# Create and checkout new branch:
git checkout -b main

# Or checkout existing branch:
git checkout main
```

### Problem: Git credential errors

**Cause**: Git cannot push to remote (authentication).

**Solution**:

```bash
# Set up SSH key (recommended):
ssh-keygen -t ed25519 -C "your.email@example.com"
cat ~/.ssh/id_ed25519.pub  # Add to GitHub

# Or use credential helper:
git config --global credential.helper store

# Or use SSH URL instead of HTTPS:
git remote set-url origin git@github.com:user/repo.git
```

---

## PR Creation Issues

### Problem: "Failed to create PR"

**Cause**: Various issues with gh CLI or repository permissions.

**Solution**:

```bash
# Check gh CLI works:
gh pr list

# Verify you can create PRs manually:
gh pr create --title "Test" --body "Test PR"

# Common issues:
# 1. No remote configured
git remote -v
git remote add origin https://github.com/user/repo.git

# 2. Branch not pushed
git push -u origin branch-name

# 3. Insufficient permissions
gh auth refresh -s repo

# Enable debug mode:
GH_DEBUG=1 lazarus heal script.py --verbose
```

### Problem: "Branch already exists"

**Cause**: Lazarus branch from previous healing still exists.

**Solution**:

```bash
# Delete old branch:
git branch -D lazarus/fix-script-name
git push origin --delete lazarus/fix-script-name

# Or configure different branch prefix:
# lazarus.yaml
git:
  branch_prefix: "auto-heal"
```

### Problem: "No changes to commit"

**Cause**: Claude didn't modify any files.

**Solution**:

```bash
# Check if files were actually changed:
git status
git diff

# Possible reasons:
# 1. Claude couldn't fix the issue
# 2. Fix was already applied
# 3. Error in Claude's execution

# Run with verbose output:
lazarus heal script.py --verbose
```

### Problem: PR created but empty

**Cause**: Changes not committed properly.

**Solution**:

```bash
# Check git history:
git log --oneline

# Verify commit has changes:
git show HEAD

# Check Lazarus logs for errors during commit
```

---

## Script Execution Failures

### Problem: Script times out

**Cause**: Script takes longer than configured timeout.

**Solution**:

```yaml
# Increase timeout in configuration:
scripts:
  - name: long-running-script
    path: scripts/slow.py
    timeout: 1800  # 30 minutes

# Or via CLI:
lazarus heal scripts/slow.py --timeout 1800
```

### Problem: Script fails with "command not found"

**Cause**: Script dependencies or interpreters not in PATH.

**Solution**:

```yaml
# Add setup commands:
scripts:
  - name: my-script
    path: scripts/test.py
    setup_commands:
      - "source venv/bin/activate"
      - "export PATH=/usr/local/bin:$PATH"

# Or specify working directory:
scripts:
  - name: my-script
    path: scripts/test.py
    working_dir: /path/to/project
```

### Problem: Script fails with "Permission denied"

**Cause**: Script not executable.

**Solution**:

```bash
# Make script executable:
chmod +x scripts/test.py

# Or run with interpreter explicitly:
python scripts/test.py  # Instead of ./scripts/test.py
```

### Problem: Environment variables not available

**Cause**: Variables not passed to script execution.

**Solution**:

```yaml
# Declare required environment variables:
scripts:
  - name: my-script
    path: scripts/test.py
    environment:
      - DATABASE_URL
      - API_KEY
      - AWS_REGION

# Ensure variables are set:
export DATABASE_URL="postgresql://..."
export API_KEY="your-key"
```

---

## Performance Issues

### Problem: Lazarus is very slow

**Causes and Solutions**:

1. **Large git history**:

```yaml
# Git operations can be slow with huge repos
# Currently no workaround, but we're working on it
```

2. **Large script output**:

```yaml
# Output is truncated automatically
# Configure in core/truncation.py if needed
```

3. **Slow Claude Code responses**:

```bash
# This depends on API response times
# Try a faster model (though less capable):
healing:
  claude_model: claude-haiku-4-5-...  # Faster but less capable
```

4. **Network latency**:

```bash
# Ensure good internet connection
# Check Claude API status: https://status.anthropic.com
```

### Problem: High memory usage

**Cause**: Large files or many concurrent operations.

**Solution**:

```bash
# Monitor memory:
ps aux | grep lazarus

# Reduce concurrent operations (if any)
# Close other applications
# Use a machine with more RAM
```

---

## Rate Limits

### Problem: "Rate limit exceeded" from Claude API

**Cause**: Too many requests to Claude API.

**Solution**:

```bash
# Wait a few minutes and try again
# The limit resets periodically

# Or reduce healing attempts:
healing:
  max_attempts: 2  # Instead of 5

# Check your API plan limits at:
# https://console.anthropic.com/settings/limits
```

### Problem: "Rate limit exceeded" from GitHub API

**Cause**: Too many GitHub API calls (gh CLI).

**Solution**:

```bash
# Check rate limit status:
gh api rate_limit

# Wait until reset time
# Or authenticate with token (higher limits):
gh auth login --with-token

# Reduce PR creation frequency
```

---

## Getting Help

### Collect Diagnostic Information

When reporting issues, include:

```bash
# 1. Lazarus version
lazarus --version

# 2. Python version
python --version

# 3. OS information
uname -a  # Linux/macOS
systeminfo  # Windows

# 4. Claude Code version
claude --version

# 5. GitHub CLI version
gh --version

# 6. Verbose output
lazarus heal script.py --verbose > debug.log 2>&1

# 7. Configuration (redact secrets!)
cat lazarus.yaml
```

### Enable Debug Logging

```yaml
# lazarus.yaml
logging:
  level: DEBUG
  console: true
  file: logs/lazarus-debug.log
```

```bash
# Run with verbose flag:
lazarus heal script.py --verbose
```

### Check Logs

```bash
# View recent history:
lazarus history --limit 20

# Check log files:
tail -f logs/lazarus.log

# Check git logs:
git log --oneline --graph
```

### Common Debug Commands

```bash
# Test Claude Code directly:
claude -p "Write a hello world Python script"

# Test GitHub CLI:
gh pr list
gh auth status

# Test git:
git status
git log --oneline -5

# Validate configuration:
lazarus validate --verbose

# Check prerequisites:
lazarus check
```

### Where to Get Support

1. **GitHub Issues**: [https://github.com/yourusername/lazarus/issues](https://github.com/yourusername/lazarus/issues)
   - Search existing issues first
   - Include diagnostic information
   - Provide minimal reproduction example

2. **GitHub Discussions**: [https://github.com/yourusername/lazarus/discussions](https://github.com/yourusername/lazarus/discussions)
   - Ask questions
   - Share use cases
   - Request features

3. **Documentation**: [https://github.com/yourusername/lazarus#readme](https://github.com/yourusername/lazarus#readme)
   - README
   - Getting Started guide
   - Configuration reference

4. **Stack Overflow**: Tag questions with `lazarus-heal`

### Before Opening an Issue

- [ ] Check existing issues and discussions
- [ ] Update to latest version: `pip install --upgrade lazarus-heal`
- [ ] Verify prerequisites: `lazarus check`
- [ ] Validate configuration: `lazarus validate`
- [ ] Try with `--verbose` flag
- [ ] Include diagnostic information (see above)
- [ ] Provide minimal reproduction example

---

## See Also

- [Getting Started](getting-started.md) - Installation and basic usage
- [Configuration](configuration.md) - Configuration reference
- [Architecture](architecture.md) - System architecture
- [Security](security.md) - Security best practices
- [FAQ](faq.md) - Frequently asked questions
