# GitHub Actions Workflows Summary

This directory contains comprehensive GitHub Actions workflows for Lazarus self-healing automation.

## Created Files

### 1. Core Workflows

#### `lazarus-scheduled.yaml` (7.6 KB)
Scheduled and manual healing workflow.
- **Triggers:** Cron schedule (every 6 hours) and manual dispatch
- **Features:** Configurable script paths, healing parameters, artifact uploads, job summaries
- **Key capabilities:** Automatic issue creation on failure, flexible configuration
- **Use case:** Regular maintenance, scheduled healing jobs

#### `lazarus-on-failure.yaml` (9.9 KB)
Reusable workflow for healing on script failures.
- **Trigger:** `workflow_call` (reusable)
- **Features:** Full parameterization, detailed outputs, comprehensive logging
- **Outputs:** `healing_result`, `pr_url`, `exit_code`, `attempts_made`
- **Use case:** CI/CD integration, automatic failure recovery

#### `lazarus-manual.yaml` (15 KB)
Feature-rich manual healing workflow.
- **Trigger:** Manual dispatch with extensive inputs
- **Features:** Input validation, dry-run mode, draft PRs, multiple Python versions
- **Special:** Comprehensive job summaries, detailed reporting, notification levels
- **Use case:** On-demand healing, testing, debugging

#### `example-integration.yaml` (12 KB)
Complete example showing integration patterns.
- **Trigger:** Push, PR, and manual dispatch
- **Features:** Full workflow pattern, PR commenting, notifications, verification
- **Demonstrates:** Proper integration, error handling, team communication
- **Use case:** Template for your own integrations

### 2. Documentation

#### `README.md` (10 KB)
Complete workflow documentation with:
- Detailed workflow descriptions
- Setup instructions
- Required secrets configuration
- Best practices
- Troubleshooting guide
- Advanced configuration examples
- Security considerations

#### `WORKFLOW_SUMMARY.md` (This file)
Quick reference for all workflow files.

## Key Features Across All Workflows

### Security
✅ Minimal permissions by default
✅ Job-specific permission elevation
✅ Secrets management best practices
✅ Branch protection integration
✅ No hardcoded credentials

### Observability
✅ Comprehensive job summaries
✅ Artifact uploads (logs, reports, history)
✅ Detailed status reporting
✅ GitHub issue creation on failures
✅ PR commenting with results

### Flexibility
✅ Configurable timeouts
✅ Multiple Python versions (3.11, 3.12, 3.13)
✅ Runner selection (self-hosted, ubuntu, macos)
✅ Dry-run mode support
✅ Matrix strategies for multiple scripts

### Robustness
✅ Input validation
✅ Error handling
✅ Timeout management
✅ Artifact retention
✅ Graceful degradation

## Usage Patterns

### Pattern 1: Scheduled Maintenance
```yaml
uses: ./.github/workflows/lazarus-scheduled.yaml
```
Best for: Regular maintenance scripts, periodic jobs

### Pattern 2: Failure Recovery
```yaml
uses: ./.github/workflows/lazarus-on-failure.yaml
with:
  script_path: './scripts/failing_script.py'
```
Best for: CI/CD integration, automatic recovery

### Pattern 3: On-Demand Healing
```yaml
# Manual trigger via GitHub UI
workflow: lazarus-manual.yaml
```
Best for: Testing, debugging, one-off fixes

### Pattern 4: Custom Integration
```yaml
# Based on example-integration.yaml
jobs:
  run-script:
    # Your script execution
  heal:
    uses: ./.github/workflows/lazarus-on-failure.yaml
```
Best for: Custom workflows, specific requirements

## Quick Start

1. **Copy workflows to your repo:**
   ```bash
   cp -r .github/workflows /your/repo/.github/
   ```

2. **Configure secrets:**
   - `ANTHROPIC_API_KEY` (required)
   - `GH_TOKEN` (recommended)
   - `SLACK_WEBHOOK_URL` (optional)

3. **Test with manual workflow:**
   - Go to Actions > Lazarus Manual Healing
   - Run with `dry_run: true`
   - Review results

4. **Enable scheduled healing:**
   - Customize cron in `lazarus-scheduled.yaml`
   - Commit and push

5. **Integrate into CI:**
   - Use `example-integration.yaml` as template
   - Customize for your needs

## Workflow Comparison

| Feature | Scheduled | On-Failure | Manual | Example |
|---------|-----------|------------|--------|---------|
| Trigger | Cron + Manual | Called | Manual | Push/PR |
| Reusable | No | Yes | No | No |
| Input Validation | Basic | No | Extensive | No |
| Dry-run Mode | No | No | Yes | No |
| Draft PR | No | No | Yes | No |
| Python Versions | Fixed | Configurable | Choice | Fixed |
| Runner Choice | Fixed | Configurable | Choice | Fixed |
| Issue Creation | Yes | No | Yes | Yes |
| PR Comments | No | Yes | No | Yes |
| Notifications | Basic | No | Configurable | Full |
| Complexity | Medium | Low | High | High |
| Best For | Automation | Integration | Testing | Learning |

## File Sizes and Complexity

| File | Size | Lines | Complexity |
|------|------|-------|------------|
| lazarus-scheduled.yaml | 7.6 KB | ~200 | Medium |
| lazarus-on-failure.yaml | 9.9 KB | ~280 | Medium |
| lazarus-manual.yaml | 15 KB | ~400 | High |
| example-integration.yaml | 12 KB | ~350 | High |
| README.md | 10 KB | ~450 | N/A |

## Integration Points

### Required Dependencies
- Python 3.11+
- `lazarus-heal` package
- Claude Code (authenticated)
- `gh` CLI (for PR creation)

### GitHub Secrets
- `ANTHROPIC_API_KEY` - Required for all workflows
- `GH_TOKEN` - Recommended for PR creation
- `SLACK_WEBHOOK_URL` - Optional for notifications

### Permissions Required
- `contents: write` - For creating branches/commits
- `pull-requests: write` - For creating PRs
- `issues: write` - For creating issues

## Customization Points

### Timing
- Cron schedules in `lazarus-scheduled.yaml`
- Timeout values in all workflows
- Retry/attempt counts

### Behavior
- PR creation (enabled/disabled)
- Draft PR mode
- Dry-run mode
- Notification levels

### Environment
- Python version
- Runner type
- Working directory
- Environment variables

## Best Practices Implemented

1. **Security First:** Minimal permissions, secrets management
2. **Observability:** Comprehensive logging and reporting
3. **Flexibility:** Configurable inputs and behaviors
4. **Robustness:** Error handling and timeout management
5. **Documentation:** Extensive inline comments and guides
6. **Testing:** Dry-run mode and validation
7. **Communication:** PR comments and notifications
8. **Maintainability:** Clear structure and naming

## Next Steps

1. Review `README.md` for detailed documentation
2. Test with `lazarus-manual.yaml` in dry-run mode
3. Customize `example-integration.yaml` for your needs
4. Enable `lazarus-scheduled.yaml` for automation
5. Monitor and adjust based on results

## Support

For detailed documentation, see:
- `README.md` - Complete workflow guide
- `../docs/github-actions.md` - Integration guide
- `../docs/configuration.md` - Configuration reference
- `../docs/troubleshooting.md` - Troubleshooting help

## Maintenance

These workflows follow GitHub Actions best practices:
- Using latest action versions (`@v4`, `@v5`, `@v7`)
- Proper permission scoping
- Artifact management with retention policies
- Timeout management
- Cache utilization for performance

Update action versions regularly:
```bash
# Check for updates
gh api repos/actions/checkout/releases/latest
gh api repos/actions/setup-python/releases/latest
gh api repos/actions/upload-artifact/releases/latest
```

---

**Created:** 2026-01-30
**Version:** 1.0.0
**Lazarus Version:** 0.1.0
