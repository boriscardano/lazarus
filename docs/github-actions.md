# GitHub Actions Integration Guide

This guide explains how to integrate Lazarus into your GitHub Actions workflows for automated script healing.

## Quick Start

### 1. Basic Setup

Add the Lazarus workflows to your repository:

```bash
# Copy workflow files to your repository
cp -r .github/workflows /path/to/your/repo/.github/

# Configure required secrets
# Go to: Settings > Secrets and variables > Actions
# Add: ANTHROPIC_API_KEY (required)
# Add: GH_TOKEN (recommended for PR creation)
```

### 2. Test with Manual Healing

Start by manually triggering healing to test your setup:

1. Go to **Actions** tab in GitHub
2. Select **Lazarus Manual Healing**
3. Click **Run workflow**
4. Fill in:
   - `script_path`: Path to your script (e.g., `./scripts/test.py`)
   - `max_attempts`: 3
   - `dry_run`: true (for first test)
5. Review the results and artifacts

### 3. Enable Scheduled Healing

The scheduled workflow runs automatically every 6 hours. To customize:

```yaml
# Edit .github/workflows/lazarus-scheduled.yaml
schedule:
  - cron: '0 */4 * * *'  # Every 4 hours
  # or
  - cron: '0 0 * * *'    # Daily at midnight
  # or
  - cron: '0 */2 * * *'  # Every 2 hours
```

### 4. Integrate into Existing Workflows

Add healing to your existing CI pipeline:

```yaml
# In your existing workflow file
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        id: tests
        continue-on-error: true
        run: pytest tests/

  heal-on-failure:
    needs: test
    if: needs.test.outputs.failed == 'true'
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: './tests/run_tests.sh'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## Workflow Types

### Scheduled Healing

**File:** `.github/workflows/lazarus-scheduled.yaml`

Automatically runs healing on a schedule or manually.

**When to use:**
- Regular maintenance scripts
- Periodic data sync jobs
- Automated reports
- Backup scripts

**Configuration:**
```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Adjust timing
  workflow_dispatch:
    # Manual trigger with inputs
```

**Manual trigger inputs:**
- `script_path`: Script to heal
- `max_attempts`: Healing attempts (default: 3)
- `create_pr`: Create PR with fix (default: true)
- `config_file`: Config file path (default: lazarus.yaml)

---

### Healing on Failure

**File:** `.github/workflows/lazarus-on-failure.yaml`

Reusable workflow for healing when scripts fail.

**When to use:**
- CI/CD pipeline failures
- Test suite failures
- Deployment script failures
- Any automated script that fails

**Example usage:**
```yaml
jobs:
  my-job:
    runs-on: ubuntu-latest
    outputs:
      failed: ${{ steps.run.outcome == 'failure' }}
    steps:
      - id: run
        continue-on-error: true
        run: ./my-script.sh

  heal:
    needs: my-job
    if: needs.my-job.outputs.failed == 'true'
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: './my-script.sh'
      max_attempts: 3
      create_pr: true
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GH_TOKEN: ${{ secrets.GH_TOKEN }}
```

**Outputs available:**
- `healing_result`: 'success' or 'failure'
- `pr_url`: URL of created PR
- `exit_code`: Exit code from healing
- `attempts_made`: Number of attempts made

---

### Manual Healing

**File:** `.github/workflows/lazarus-manual.yaml`

Full-featured manual healing with all options.

**When to use:**
- On-demand healing
- Testing new scripts
- Debugging healing issues
- One-off fixes

**Features:**
- Input validation
- Dry-run mode
- Draft PR support
- Multiple Python versions
- Flexible runner selection
- Detailed reporting

**Best practices:**
1. Always test with `dry_run: true` first
2. Use `draft_pr: true` for critical scripts
3. Enable `verbose: true` for debugging
4. Start with fewer `max_attempts` to save time

---

### Example Integration

**File:** `.github/workflows/example-integration.yaml`

Complete example showing best practices.

**Features:**
- Script execution with failure handling
- Automatic healing on failure
- PR commenting with results
- Healing verification
- Team notifications
- Issue creation on failures

**Use this as a template** for your own workflows.

---

## Configuration Examples

### Example 1: Simple Script Healing

```yaml
name: Heal Data Sync Script

on:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  heal:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run Lazarus
        run: lazarus run ./scripts/sync_data.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Example 2: Multi-Script Healing

```yaml
name: Heal Multiple Scripts

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  heal:
    strategy:
      matrix:
        script:
          - './scripts/backup.sh'
          - './scripts/cleanup.py'
          - './scripts/report.js'
      fail-fast: false
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: ${{ matrix.script }}
      max_attempts: 2
      create_pr: true
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Example 3: Environment-Specific Healing

```yaml
name: Environment-Aware Healing

on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, staging, prod]
        required: true

jobs:
  heal:
    runs-on: self-hosted
    environment: ${{ github.event.inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      - name: Heal with environment
        run: |
          lazarus heal ./scripts/deploy.sh \
            --env ${{ github.event.inputs.environment }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Example 4: PR Integration

```yaml
name: PR Checks with Healing

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      failed: ${{ steps.test.outcome == 'failure' }}
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        id: test
        continue-on-error: true
        run: npm test

  heal:
    needs: test
    if: needs.test.outputs.failed
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: './scripts/run_tests.sh'
      create_pr: true
      draft_pr: true  # Review before merge
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  comment:
    needs: [test, heal]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Comment results
        uses: actions/github-script@v7
        with:
          script: |
            const healingSucceeded = '${{ needs.heal.outputs.healing_result }}' === 'success';
            const prUrl = '${{ needs.heal.outputs.pr_url }}';

            let comment = healingSucceeded
              ? `✅ Tests failed but Lazarus auto-healed them! See ${prUrl}`
              : '❌ Tests failed and healing was unsuccessful. Manual review needed.';

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

---

## Advanced Features

### Caching for Faster Runs

```yaml
- name: Cache Lazarus
  uses: actions/cache@v4
  with:
    path: ~/.local/lib/python3.11/site-packages
    key: ${{ runner.os }}-lazarus-${{ hashFiles('**/pyproject.toml') }}
```

### Conditional PR Creation

```yaml
- name: Heal script
  run: |
    CREATE_PR="false"
    if [ "${{ github.ref_name }}" = "main" ]; then
      CREATE_PR="true"
    fi
    lazarus heal ./script.py --create-pr=$CREATE_PR
```

### Custom Notifications

```yaml
- name: Send Slack notification
  if: steps.healing.outputs.result == 'success'
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "Healing succeeded! PR: ${{ steps.healing.outputs.pr_url }}"
      }'
```

### Artifact Management

```yaml
- name: Upload comprehensive logs
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: healing-${{ github.run_id }}
    path: |
      .lazarus/**
      logs/**
      *.log
    retention-days: 90
```

---

## Self-Hosted Runner Setup

For optimal performance, use self-hosted runners with Lazarus pre-installed.

### macOS Setup

```bash
# Install Lazarus
uv pip install lazarus-heal

# Setup launchd service
cp runner-setup/macos-launchd.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/lazarus.runner.plist
```

### Linux Setup

```bash
# Install Lazarus
uv pip install lazarus-heal

# Setup systemd service
sudo cp runner-setup/linux-systemd.service /etc/systemd/system/lazarus-runner.service
sudo systemctl enable lazarus-runner
sudo systemctl start lazarus-runner
```

See [Self-Hosted Runner Setup](./self-hosted-runner.md) for detailed instructions.

---

## Security Best Practices

### 1. Use Secrets Properly

```yaml
# ✅ GOOD: Use secrets for sensitive data
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

# ❌ BAD: Never hardcode secrets
env:
  ANTHROPIC_API_KEY: "sk-ant-..."
```

### 2. Minimal Permissions

```yaml
permissions:
  contents: read  # Default

jobs:
  heal:
    permissions:
      contents: write       # Only for PR creation
      pull-requests: write  # Only for PR creation
```

### 3. Use GH_TOKEN for PRs

```yaml
# ✅ GOOD: Custom token with minimal scopes
token: ${{ secrets.GH_TOKEN }}

# ⚠️ LIMITED: Default token has restrictions
token: ${{ secrets.GITHUB_TOKEN }}
```

### 4. Review Healing PRs

```yaml
# Create as draft for review
draft_pr: true

# Enable branch protection
# Settings > Branches > Add rule
# - Require pull request reviews
# - Require status checks
```

### 5. Enable Secret Scanning

```bash
# In repository settings:
# Security > Code security and analysis
# Enable: Secret scanning
# Enable: Push protection
```

---

## Troubleshooting

### Common Issues

#### "ANTHROPIC_API_KEY not found"

**Solution:**
```bash
# Go to: Settings > Secrets and variables > Actions
# New repository secret:
# Name: ANTHROPIC_API_KEY
# Value: sk-ant-...
```

#### "Permission denied" when creating PR

**Solution:**
```yaml
# Create a Personal Access Token (PAT):
# Settings > Developer settings > Personal access tokens
# Scopes: repo, workflow
# Add as GH_TOKEN secret

# Use in workflow:
with:
  token: ${{ secrets.GH_TOKEN }}
```

#### Workflow times out

**Solution:**
```yaml
# Increase timeout
timeout-minutes: 30

# Or reduce attempts
with:
  max_attempts: 2
  timeout_minutes: 10
```

#### Script path not found

**Solution:**
```yaml
# Use relative path from repo root
script_path: './scripts/my_script.py'  # ✅
script_path: 'my_script.py'            # ❌

# Verify in workflow:
- name: Check script exists
  run: test -f ./scripts/my_script.py
```

#### Self-hosted runner issues

**Solution:**
```bash
# On runner machine:
# 1. Check Lazarus installation
lazarus check

# 2. Verify Claude Code auth
claude --version

# 3. Check gh CLI
gh auth status

# 4. View runner logs
# macOS: ~/Library/Logs/lazarus-runner/
# Linux: journalctl -u lazarus-runner
```

---

## Monitoring and Analytics

### Job Summaries

All workflows generate detailed job summaries:
- Configuration used
- Healing results
- PR URLs
- Error details
- Logs excerpts

Access via: Actions > Workflow run > Summary

### Artifacts

Download artifacts for detailed analysis:
- Healing logs
- History files
- JSON reports

Retention: 30-90 days (configurable)

### GitHub Insights

Track healing effectiveness:
```bash
# View workflow runs
gh run list --workflow=lazarus-scheduled.yaml

# View specific run
gh run view <run-id>

# Download artifacts
gh run download <run-id>
```

---

## Best Practices Summary

1. **Start with dry-run mode** to test healing
2. **Use self-hosted runners** for better performance
3. **Enable verbose logging** during initial setup
4. **Create draft PRs** for critical scripts
5. **Configure appropriate timeouts** for your scripts
6. **Review healing PRs** before merging
7. **Monitor healing success rates** over time
8. **Adjust max_attempts** based on script complexity
9. **Use matrix strategies** for multiple scripts
10. **Set up proper notifications** for your team

---

## Additional Resources

- [Lazarus Configuration](./configuration.md)
- [Self-Hosted Runner Setup](./self-hosted-runner.md)
- [Security Best Practices](./security.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## Support

For help with GitHub Actions integration:
- [GitHub Issues](https://github.com/boriscardano/lazarus/issues)
- [Discussions](https://github.com/boriscardano/lazarus/discussions)
- [Documentation](https://github.com/boriscardano/lazarus/docs)
