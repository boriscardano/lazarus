# Lazarus GitHub Actions Workflows

This directory contains GitHub Actions workflows for automating script healing with Lazarus.

## Available Workflows

### 1. Scheduled Healing (`lazarus-scheduled.yaml`)

Runs healing on a schedule or manually triggered.

**Triggers:**
- **Schedule:** Every 6 hours by default (configurable via cron)
- **Manual:** `workflow_dispatch` with customizable inputs

**Features:**
- Configurable script path and healing parameters
- Full logging and artifact uploads
- Job summaries with healing details
- Automatic issue creation on failure

**Usage:**
```yaml
# Scheduled run (configured in workflow)
# Runs automatically every 6 hours

# Manual trigger via GitHub UI:
# Actions > Lazarus Scheduled Healing > Run workflow
# Provide inputs: script_path, max_attempts, create_pr, config_file
```

**Required Secrets:**
- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude Code
- `GH_TOKEN`: (Optional) GitHub token with repo and PR permissions

---

### 2. Healing on Failure (`lazarus-on-failure.yaml`)

Reusable workflow for healing scripts when they fail.

**Triggers:**
- `workflow_call` - Called from other workflows

**Features:**
- Reusable across multiple workflows
- Configurable inputs for all healing parameters
- Detailed output including PR URL and healing status
- Comprehensive error reporting
- Job summaries and artifact uploads

**Usage:**
```yaml
jobs:
  heal-failed-script:
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: './scripts/my_script.py'
      max_attempts: 3
      create_pr: true
      timeout_minutes: 15
      runner: 'self-hosted'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GH_TOKEN: ${{ secrets.GH_TOKEN }}
```

**Inputs:**
- `script_path` (required): Path to failing script
- `max_attempts` (default: 3): Max healing attempts
- `create_pr` (default: true): Create PR with fix
- `timeout_minutes` (default: 15): Timeout per healing attempt
- `working_directory` (default: '.'): Working directory
- `continue_on_error` (default: false): Continue if healing fails
- `python_version` (default: '3.11'): Python version
- `runner` (default: 'self-hosted'): Runner type

**Outputs:**
- `healing_result`: 'success' or 'failure'
- `pr_url`: URL of created PR (if applicable)
- `exit_code`: Exit code from healing process
- `attempts_made`: Number of attempts made

---

### 3. Manual Healing (`lazarus-manual.yaml`)

On-demand healing with full control over all parameters.

**Triggers:**
- `workflow_dispatch` - Manual trigger only

**Features:**
- Comprehensive input validation
- Dry-run mode for testing
- Detailed job summaries with results
- Configurable notifications
- Draft PR support
- Multiple Python version support
- Choice of runners (self-hosted, ubuntu, macos)

**Usage:**
```yaml
# Via GitHub UI:
# Actions > Lazarus Manual Healing > Run workflow
# Provide all desired inputs

# Key inputs:
# - script_path: Required path to script
# - max_attempts: 1-10 attempts
# - create_pr: true/false
# - draft_pr: true/false
# - dry_run: true/false (analyze only, no changes)
# - timeout_minutes: Timeout per attempt
# - python_version: 3.11, 3.12, or 3.13
# - runner_type: self-hosted, ubuntu-latest, macos-latest
# - verbose: Enable detailed logging
# - notification_level: all, failures-only, or none
```

**Required Secrets:**
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `GH_TOKEN`: (Optional) GitHub token

---

### 4. Example Integration (`example-integration.yaml`)

Example showing how to integrate Lazarus into existing CI/CD pipelines.

**Triggers:**
- `push` to main/master branches
- `pull_request` to main/master branches
- `workflow_dispatch` for testing

**Features:**
- Demonstrates typical CI workflow with healing
- Shows how to call the reusable healing workflow
- Includes PR commenting with results
- Optional verification of healing
- Slack notifications
- Issue creation on failures

**Integration Pattern:**
```yaml
jobs:
  # 1. Run your script
  run-script:
    runs-on: ubuntu-latest
    steps:
      - name: Run script
        id: run_script
        continue-on-error: true  # Don't fail yet
        run: ./scripts/my_script.sh

  # 2. Heal if failed
  heal-on-failure:
    needs: run-script
    if: needs.run-script.outputs.script_failed == 'true'
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: './scripts/my_script.sh'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  # 3. Comment results on PR
  comment-results:
    needs: [run-script, heal-on-failure]
    if: github.event_name == 'pull_request'
    # ... comment with results
```

---

## Setup Instructions

### 1. Prerequisites

- Self-hosted runner (recommended) or GitHub-hosted runner
- Python 3.11+ installed on runner
- `lazarus-heal` package installed on runner
- Claude Code configured and authenticated
- `gh` CLI installed for PR creation

### 2. Required Secrets

Configure these secrets in your repository (Settings > Secrets and variables > Actions):

| Secret | Description | Required |
|--------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude Code | Yes |
| `GH_TOKEN` | GitHub PAT with `repo` and `pr` scopes | Recommended |
| `SLACK_WEBHOOK_URL` | (Optional) For Slack notifications | No |

### 3. Self-Hosted Runner Setup

For best results, use a self-hosted runner with Lazarus pre-installed:

```bash
# On your self-hosted runner
pip install lazarus-heal

# Verify installation
lazarus check

# Configure Claude Code
# Follow instructions at: https://github.com/anthropics/claude-code
```

See `/runner-setup` directory for detailed setup guides:
- `macos-launchd.sh` - macOS setup with launchd
- `linux-systemd.sh` - Linux setup with systemd

### 4. Workflow Configuration

1. **Copy workflows to your repository:**
   ```bash
   cp -r .github/workflows /path/to/your/repo/.github/
   ```

2. **Customize for your needs:**
   - Update `script_path` in workflows
   - Adjust cron schedule in `lazarus-scheduled.yaml`
   - Modify notification settings
   - Configure runner types

3. **Test the workflows:**
   - Use `lazarus-manual.yaml` first to test healing
   - Enable `dry_run` mode to preview changes
   - Verify PR creation works correctly

---

## Workflow Permissions

All workflows follow security best practices with minimal permissions:

### Default Permissions
```yaml
permissions:
  contents: read  # Read repository contents
```

### Job-Specific Permissions
```yaml
permissions:
  contents: write       # Create branches and commits
  pull-requests: write  # Create and comment on PRs
  issues: write         # Create issues on failures
```

---

## Best Practices

### 1. Use Self-Hosted Runners

Self-hosted runners provide:
- Faster execution (no cold starts)
- Pre-installed dependencies
- Access to internal resources
- Better security control
- Cost savings for frequent runs

### 2. Configure Appropriate Timeouts

```yaml
# Per-attempt timeout (default: 10 minutes)
timeout_minutes: 10

# Job-level timeout (default: 30 minutes)
timeout-minutes: 30
```

### 3. Use Draft PRs for Critical Scripts

```yaml
draft_pr: true  # Review before marking ready
```

### 4. Enable Verbose Logging During Setup

```yaml
verbose: true  # Detailed logs for debugging
```

### 5. Start with Dry Run Mode

```yaml
dry_run: true  # Analyze without making changes
```

### 6. Configure Appropriate Schedules

```yaml
# Recommendations:
# - Non-critical scripts: Every 12 hours
# - Important scripts: Every 6 hours
# - Critical scripts: Every 2-4 hours
# - High-frequency scripts: Every hour

schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
```

---

## Troubleshooting

### Common Issues

#### 1. "ANTHROPIC_API_KEY not found"
**Solution:** Configure the secret in repository settings.

#### 2. "Script not found"
**Solution:** Verify script path is relative to repository root.

#### 3. "gh: command not found"
**Solution:** Install GitHub CLI on your runner.

#### 4. "Permission denied" when creating PR
**Solution:** Use `GH_TOKEN` with appropriate permissions instead of `GITHUB_TOKEN`.

#### 5. Workflow times out
**Solution:** Increase `timeout_minutes` or reduce `max_attempts`.

### Debugging Workflows

1. **Enable verbose logging:**
   ```yaml
   verbose: true
   ```

2. **Download artifacts:**
   - Go to workflow run
   - Download "healing-logs" artifact
   - Review `.lazarus/logs/` for details

3. **Check job summaries:**
   - View job summary on workflow run page
   - Contains key metrics and excerpts

4. **Review healing history:**
   ```bash
   lazarus history --verbose
   ```

---

## Advanced Configuration

### Custom Notification Webhooks

```yaml
- name: Send custom notification
  run: |
    curl -X POST ${{ secrets.WEBHOOK_URL }} \
      -H 'Content-Type: application/json' \
      -d '{
        "result": "${{ steps.healing.outputs.result }}",
        "pr_url": "${{ steps.healing.outputs.pr_url }}"
      }'
```

### Matrix Healing (Multiple Scripts)

```yaml
jobs:
  heal-multiple:
    strategy:
      matrix:
        script:
          - './scripts/script1.py'
          - './scripts/script2.sh'
          - './scripts/script3.js'
    uses: ./.github/workflows/lazarus-on-failure.yaml
    with:
      script_path: ${{ matrix.script }}
```

### Conditional PR Creation

```yaml
create_pr: ${{ github.event_name == 'schedule' }}
```

### Environment-Specific Healing

```yaml
- name: Set environment
  run: |
    if [ "${{ github.ref_name }}" = "main" ]; then
      echo "ENV=production" >> $GITHUB_ENV
    else
      echo "ENV=staging" >> $GITHUB_ENV
    fi

- name: Heal with environment
  run: lazarus heal ./script.py --env ${{ env.ENV }}
```

---

## Security Considerations

1. **Never commit secrets** to workflow files
2. **Use scoped tokens** with minimal permissions
3. **Enable branch protection** for healing PRs
4. **Review healing PRs** before merging to production
5. **Audit healing logs** regularly
6. **Use secret scanning** to prevent leaks
7. **Limit workflow permissions** to minimum required
8. **Enable required reviews** for healing PRs

---

## Additional Resources

- [Lazarus Documentation](../docs/)
- [Configuration Guide](../docs/configuration.md)
- [Self-Hosted Runner Setup](../docs/self-hosted-runner.md)
- [Security Best Practices](../docs/security.md)
- [Troubleshooting Guide](../docs/troubleshooting.md)

---

## Support

For issues or questions:
- [GitHub Issues](https://github.com/boriscardano/lazarus/issues)
- [Discussions](https://github.com/boriscardano/lazarus/discussions)
- [Documentation](https://github.com/boriscardano/lazarus/docs)
