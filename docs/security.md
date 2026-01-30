# Security

Security considerations and best practices for using Lazarus.

## Table of Contents

- [Overview](#overview)
- [Data Sent to Claude](#data-sent-to-claude)
- [Secrets Redaction](#secrets-redaction)
- [Access Control](#access-control)
- [Code Review Requirements](#code-review-requirements)
- [CI/CD Security](#cicd-security)
- [Self-Hosted Runners](#self-hosted-runners)
- [Best Practices](#best-practices)
- [Threat Model](#threat-model)
- [Audit Logging](#audit-logging)

---

## Overview

Lazarus is a tool that sends code and error context to Claude AI for automated healing. This requires careful security considerations to protect sensitive data, credentials, and production systems.

### Security Philosophy

1. **Defense in Depth**: Multiple layers of security controls
2. **Principle of Least Privilege**: Minimal permissions required
3. **Secure by Default**: Safe defaults for all configurations
4. **Transparency**: Clear documentation of what data is sent where
5. **Auditability**: Comprehensive logging of all operations

### Security Features

- Automatic secrets redaction before sending to AI
- Configurable redaction patterns for custom secrets
- Limited Claude Code tool access (Edit, Read, Write only by default)
- PR-based workflow requiring human review
- Comprehensive audit logging
- Environment variable filtering

---

## Data Sent to Claude

Lazarus sends the following information to Claude Code (and thus to Anthropic's Claude API):

### Always Sent (After Redaction)

1. **Script Content**:
   - Full source code of the failing script
   - Redacted for secrets before sending

2. **Execution Context**:
   - stdout output (truncated and redacted)
   - stderr output (truncated and redacted)
   - Exit code
   - Execution duration

3. **Git Context**:
   - Recent commit messages (last 5 commits, redacted)
   - Uncommitted changes (git diff, redacted)
   - Current branch name
   - File paths

4. **System Context**:
   - Operating system and version
   - Shell type
   - Safe environment variables only (PATH, HOME, USER, etc.)

5. **Custom Prompt** (if configured):
   - Additional context from `custom_prompt` field

### Never Sent

- Full environment variables (only safe ones like PATH, HOME, USER)
- Sensitive files (forbidden_files patterns)
- Files outside allowed_files patterns
- Redacted secrets (API keys, passwords, tokens)
- Git repository remotes (no remote URLs)
- User's personal information beyond OS/shell

### Data Retention

Lazarus itself does not store data long-term:
- Local logs (configurable retention)
- Git commits (standard git retention)
- Healing history (JSON files on disk, configurable location)

Data sent to Claude is subject to [Anthropic's retention policies](https://www.anthropic.com/legal/privacy).

---

## Secrets Redaction

Lazarus automatically redacts secrets before sending context to Claude.

### Built-in Redaction Patterns

The following patterns are redacted by default:

```python
# API Keys
api_key = "abc123..."  # → api_key = "[REDACTED:api_key]"

# Access Tokens
token = "ghp_abc123..."  # → token = "[REDACTED:token]"

# Passwords
password = "mysecret"  # → password = "[REDACTED:password]"

# AWS Credentials
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"  # → "[REDACTED:aws_access_key]"
aws_secret_access_key = "wJalrXUtn..."  # → "[REDACTED:aws_secret_key]"

# Private Keys
-----BEGIN PRIVATE KEY-----  # → [REDACTED:private_key_block]

# Bearer Tokens
Authorization: Bearer abc123  # → Authorization: [REDACTED:bearer]
```

### Custom Redaction Patterns

Add custom patterns for your specific secrets:

```yaml
# lazarus.yaml
security:
  additional_patterns:
    # Database passwords
    - "(?i)(db_password|database_password)[\s=:]+['\"]?([^\s'\"]{8,})['\"]?"

    # Stripe keys
    - "(?i)(stripe[_-]?key)[\s=:]+['\"]?(sk_live_[a-zA-Z0-9]{24,})['\"]?"

    # Custom API tokens
    - "(?i)(myapp[_-]?token)[\s=:]+['\"]?([a-zA-Z0-9_\-]{32,})['\"]?"

    # IP addresses (if sensitive in your context)
    - "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"
```

### Redaction Verification

Verify redaction is working:

```bash
# Run with verbose output and check logs
lazarus heal script.py --verbose 2>&1 | grep -i "password"

# Should show [REDACTED:...] instead of actual secrets
```

### Redaction Limitations

**Important**: Redaction is pattern-based and may not catch all secrets:

- Custom secret formats not in standard patterns
- Secrets in binary files or encoded formats
- Secrets split across multiple lines
- Very short secrets (< 8 characters)

**Always review PRs** to ensure no secrets are committed.

---

## Access Control

### GitHub Permissions

Minimum required permissions for Lazarus:

**Repository Permissions** (for pr creation):
- Contents: Read and write
- Pull requests: Read and write

**Personal Access Token Scopes**:
```bash
# Required scopes when using gh CLI
gh auth login -s repo,workflow
```

### Service Account Recommendation

For production use, create a dedicated service account:

```bash
# 1. Create GitHub service account
#    - Username: lazarus-bot
#    - Email: lazarus-bot@yourcompany.com

# 2. Grant minimal permissions
#    - Repository access only
#    - No admin rights
#    - No organization access

# 3. Use separate API keys
export ANTHROPIC_API_KEY="sk-ant-lazarus-only-key"
export GH_TOKEN="ghp_lazarus_bot_token"
```

### Anthropic API Key Security

```bash
# Use separate API key for Lazarus (not your personal key)
# Set spending limits in Anthropic Console:
# https://console.anthropic.com/settings/limits

# Rotate keys regularly (every 90 days)

# Never commit API keys to git:
echo "ANTHROPIC_API_KEY" >> .gitignore
echo "GH_TOKEN" >> .gitignore
```

### File Access Control

Limit which files Claude can modify:

```yaml
scripts:
  - name: my-script
    path: scripts/backup.py
    allowed_files:
      - "scripts/**/*.py"      # Only Python scripts
      - "config/backup.yaml"   # And specific config
    forbidden_files:
      - "**/*.env"             # Never touch .env files
      - "secrets/**"           # Or secrets directory
      - "*.pem"                # Or private keys
      - ".git/**"              # Or git internals
```

---

## Code Review Requirements

**NEVER auto-merge Lazarus PRs**. Always require human review.

### Review Checklist

When reviewing a Lazarus PR:

- [ ] **No secrets committed**
  - Check diff for API keys, passwords, tokens
  - Verify redaction worked correctly
  - Look for base64 encoded secrets

- [ ] **Changes are appropriate**
  - Fix addresses the actual error
  - No unnecessary changes
  - No suspicious code additions

- [ ] **Tests pass**
  - CI/CD checks passed
  - Manual testing if needed
  - No regressions introduced

- [ ] **Security implications**
  - No new vulnerabilities introduced
  - No privilege escalation
  - No data exposure risks

- [ ] **Code quality**
  - Follows project conventions
  - Well-commented if complex
  - No obvious bugs

### Dangerous Patterns to Watch For

```python
# 1. Arbitrary code execution
exec(user_input)  # DANGER!
eval(data)        # DANGER!

# 2. Command injection
os.system(f"cmd {user_input}")  # DANGER!

# 3. Path traversal
open(f"../{user_path}")  # DANGER!

# 4. SQL injection
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")  # DANGER!

# 5. Hardcoded secrets (even if temporary)
api_key = "sk-ant-abc123"  # DANGER!
```

### GitHub Branch Protection

Configure branch protection rules:

```yaml
# .github/settings.yml (using Probot Settings)
branches:
  - name: main
    protection:
      required_pull_request_reviews:
        required_approving_review_count: 1
        dismiss_stale_reviews: true
      required_status_checks:
        strict: true
        contexts:
          - tests
          - lint
      enforce_admins: false
      restrictions: null
```

---

## CI/CD Security

### GitHub Actions Configuration

```yaml
# .github/workflows/lazarus.yaml
name: Lazarus Healing

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  heal:
    runs-on: self-hosted  # Use self-hosted for sensitive repos
    permissions:
      contents: write      # To create branches
      pull-requests: write # To create PRs

    steps:
      - uses: actions/checkout@v4

      - name: Run Lazarus
        run: lazarus heal scripts/critical.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          # Never use ${{ secrets.GITHUB_TOKEN }} if you can avoid it
          # gh CLI will use its own auth
```

### Secrets Management

```bash
# Store secrets in GitHub Secrets (not in code)
# Settings > Secrets and variables > Actions

# Required secrets:
# - ANTHROPIC_API_KEY: Claude API key
# - SLACK_WEBHOOK_URL: Slack notifications (optional)

# DO NOT store:
# - Production database credentials
# - SSH private keys
# - Certificate private keys
# - OAuth tokens
```

### Network Security

```yaml
# Restrict outbound network access in self-hosted runners
# Allow only necessary endpoints:
# - api.anthropic.com (Claude API)
# - github.com (git push, gh CLI)
# - Your notification webhooks
```

---

## Self-Hosted Runners

When using self-hosted GitHub Actions runners:

### Runner Isolation

```bash
# Run in isolated environment:
# 1. Dedicated VM or container
# 2. No access to production systems
# 3. No sensitive data on runner
# 4. Ephemeral runners (destroyed after each job)
```

### Network Segmentation

```bash
# Segment runner network:
# - Separate VLAN/subnet
# - Firewall rules limiting outbound
# - No direct access to production databases
# - Jump box for any necessary access
```

### Monitoring

```bash
# Monitor runner activity:
# - Log all command executions
# - Alert on suspicious activity
# - Regular security audits
# - Automated vulnerability scanning
```

See [Self-Hosted Runner Setup](self-hosted-runner.md) for detailed configuration.

---

## Best Practices

### 1. Start with Draft PRs

```yaml
# lazarus.yaml
git:
  draft_pr: true  # Always create as draft for review
```

### 2. Limit Healing Scope

```yaml
scripts:
  - name: critical-script
    path: scripts/backup.py
    allowed_files:
      - "scripts/backup.py"  # Only this one file
    forbidden_files:
      - "**/*"               # Everything else forbidden
```

### 3. Use Separate Environments

```bash
# Test Lazarus in staging first
# Separate API keys for staging/production
# Different service accounts per environment
```

### 4. Regular Security Audits

```bash
# Monthly review:
# - Healing history for anomalies
# - All Lazarus PRs created
# - API key usage/costs
# - Access logs

lazarus history --limit 100 > audit.log
```

### 5. Principle of Least Privilege

```yaml
healing:
  allowed_tools:
    - Edit   # Allow editing files
    - Read   # Allow reading files
    # Write - Only if absolutely needed
    # Bash  - NEVER allow in production
```

### 6. Keep Lazarus Updated

```bash
# Regular updates for security patches
pip install --upgrade lazarus-heal

# Subscribe to security advisories:
# Watch repository on GitHub
# Enable security alerts
```

### 7. Monitor API Usage

```bash
# Monitor Anthropic API usage:
# - Track cost/usage trends
# - Alert on unusual spikes
# - Set spending limits

# Check at: https://console.anthropic.com/settings/limits
```

---

## Threat Model

### Threat: Secrets Leaked to AI

**Risk**: Secrets sent to Claude despite redaction

**Mitigations**:
- Automatic redaction with configurable patterns
- Environment variable filtering
- Always review PRs before merging
- Use separate API keys (not production keys)

**Residual Risk**: Low (with proper configuration)

### Threat: Malicious Code Injection

**Risk**: Claude generates malicious code

**Mitigations**:
- Human review required (draft PRs by default)
- Limited tool access (no Bash in production)
- File access restrictions (allowed_files/forbidden_files)
- Branch protection rules

**Residual Risk**: Low (requires human approval)

### Threat: Credential Compromise

**Risk**: Anthropic or GitHub credentials stolen

**Mitigations**:
- Separate service account
- Minimal permissions
- Key rotation every 90 days
- Spending limits on API keys
- Monitor for unauthorized usage

**Residual Risk**: Medium (external dependency)

### Threat: Dependency Vulnerability

**Risk**: Vulnerability in Lazarus dependencies

**Mitigations**:
- Regular dependency updates
- Automated vulnerability scanning
- Minimal dependencies
- Pin dependency versions

**Residual Risk**: Low (active maintenance)

### Threat: Insider Threat

**Risk**: Malicious use of Lazarus by authorized user

**Mitigations**:
- Audit logging of all operations
- PR review requirements
- Separate service account (not personal)
- Regular access reviews

**Residual Risk**: Medium (requires processes)

---

## Audit Logging

### What is Logged

Lazarus logs:

1. **All healing sessions**:
   - Script executed
   - Timestamp
   - Duration
   - Success/failure
   - Attempts made

2. **Git operations**:
   - Branches created
   - Commits made
   - PRs created
   - PR URLs

3. **Errors and exceptions**:
   - Configuration errors
   - Execution failures
   - Network errors

### Log Locations

```bash
# Healing history (JSON):
~/.lazarus/history/

# Application logs (if configured):
logs/lazarus.log

# Git history:
git log --author="Lazarus"
git log --grep="Auto-heal"
```

### Log Retention

```yaml
# Configure log retention
logging:
  file: logs/lazarus.log
  rotation: 50  # MB per file
  retention: 30 # Number of files to keep
```

### Centralized Logging

For enterprise use, forward logs to SIEM:

```bash
# Example: Forward to Splunk
tail -f logs/lazarus.log | /opt/splunkforwarder/bin/splunk add forward-server

# Or use structured logging:
# Configure logging.formatters in Python logging
```

### Compliance

Logs include:
- **Who**: Service account (via git committer)
- **What**: Script healed, changes made
- **When**: Timestamp in ISO 8601 format
- **Where**: Repository and branch
- **Why**: Error message and fix explanation
- **How**: Healing attempts and verification

---

## Security Updates

### Reporting Vulnerabilities

See [SECURITY.md](../SECURITY.md) in project root for:
- How to report security vulnerabilities
- Response timeline
- Supported versions
- Security contact information

### Security Notifications

Stay informed:

1. **Watch repository on GitHub**:
   - Settings > Watch > Custom > Security alerts

2. **Subscribe to releases**:
   - Get notified of new versions

3. **Enable Dependabot**:
   - Automatic dependency updates
   - Vulnerability alerts

---

## See Also

- [Configuration Reference](configuration.md) - Security configuration options
- [Getting Started](getting-started.md) - Secure installation guide
- [Troubleshooting](troubleshooting.md) - Security-related issues
- [Self-Hosted Runner Setup](self-hosted-runner.md) - Runner security
- [SECURITY.md](../SECURITY.md) - Vulnerability reporting
