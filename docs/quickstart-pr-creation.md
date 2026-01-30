# PR Creation Quick Start Guide

Get Lazarus PR creation up and running in 5 minutes.

## Prerequisites

### 1. Install GitHub CLI

```bash
# macOS
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh

# Windows
winget install GitHub.cli

# Verify installation
gh --version
```

### 2. Authenticate with GitHub

```bash
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

### 3. Verify Authentication

```bash
gh auth status
```

You should see: "✓ Logged in to github.com as <your-username>"

## Quick Setup

### 1. Enable PR Creation in Config

Edit your `lazarus.yaml`:

```yaml
git:
  create_pr: true
  branch_prefix: "lazarus/fix"
  draft_pr: false
```

### 2. Test Prerequisites

Run the example to verify everything works:

```bash
python examples/pr_creation_example.py
```

You should see:
```
✅ GitHub CLI (gh): Installed
✅ Authentication: Authenticated
✅ All prerequisites met for PR creation!
```

## Your First Healing with PR

### 1. Create a Failing Script

```bash
# Create a test script
cat > scripts/test_fail.py << 'EOF'
#!/usr/bin/env python3
import nonexistent_module

print("This will fail")
EOF

chmod +x scripts/test_fail.py
```

### 2. Add to Lazarus Config

```yaml
scripts:
  - name: test-script
    path: scripts/test_fail.py
    timeout: 60
```

### 3. Run Healing

```bash
lazarus heal scripts/test_fail.py
```

### 4. Expected Result

Lazarus will:
1. Detect the import error
2. Use Claude Code to fix it
3. Create a branch: `lazarus/fix/test-fail`
4. Push changes
5. Create a PR with details

You'll see output like:
```
✅ Healing successful after 1 attempt!
🔀 PR created: https://github.com/user/repo/pull/123
```

## Configuration Options

### Basic Configuration

```yaml
git:
  create_pr: true              # Enable PR creation
  branch_prefix: "lazarus/fix" # Branch name prefix
  draft_pr: false             # Create as draft
```

### Custom Templates

```yaml
git:
  pr_title_template: "fix: heal {script_name}"
  pr_body_template: |
    ## Auto-Healing Report

    Script: {script_path}
    Attempts: {attempts}
    Duration: {duration:.2f}s
```

### Labels and Assignees (Future)

```yaml
git:
  labels: ["lazarus", "auto-heal", "needs-review"]
  assignees: ["team-lead"]
```

## Common Workflows

### Workflow 1: Auto-Merge After Tests

```yaml
git:
  create_pr: true
  draft_pr: false
  auto_merge: true  # Not yet implemented
```

Set up GitHub branch protection:
1. Require status checks
2. Enable auto-merge
3. PRs merge automatically when checks pass

### Workflow 2: Review Before Merge

```yaml
git:
  create_pr: true
  draft_pr: false
```

Team reviews PRs manually before merging.

### Workflow 3: Draft for Complex Changes

```yaml
git:
  create_pr: true
  draft_pr: true
```

Creates draft PRs that require manual "Ready for review".

## Troubleshooting

### "gh: command not found"

**Solution**: Install GitHub CLI (see Prerequisites)

### "not authenticated"

**Solution**: Run `gh auth login`

### "Not a git repository"

**Solution**: Initialize git:
```bash
git init
git remote add origin <your-repo-url>
```

### "Permission denied (push)"

**Solution**: Verify git remote access:
```bash
git remote -v
gh auth refresh -s repo
```

### "failed to create pull request"

**Possible causes:**
1. No changes to commit
2. Branch protection rules
3. Insufficient permissions

**Solution**: Check git status and GitHub permissions

## Best Practices

### 1. Test Before Production

Run Lazarus manually first:
```bash
lazarus heal scripts/important.py --dry-run
```

### 2. Use Branch Protection

Configure GitHub branch protection:
- Require PR reviews
- Require status checks
- Restrict push to main

### 3. Review Auto-Generated PRs

Always review PRs before merging, especially for:
- Production scripts
- Database migrations
- Security-sensitive code

### 4. Monitor PR Activity

Set up Slack/Discord notifications for PR creation:
```yaml
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_success: true
```

## Next Steps

1. **Read Full Documentation**: `docs/git-integration.md`
2. **Run Examples**: `python examples/pr_creation_example.py`
3. **Configure Monitoring**: Set up scheduled healing
4. **Setup CI/CD**: Configure GitHub Actions
5. **Add Notifications**: Enable Slack/Discord alerts

## Quick Reference

### Check Prerequisites
```bash
# Check gh CLI
gh --version

# Check authentication
gh auth status

# Test with example
python examples/pr_creation_example.py
```

### Manual PR Creation
```python
from pathlib import Path
from lazarus.config.schema import GitConfig
from lazarus.git.pr import PRCreator

config = GitConfig(create_pr=True, branch_prefix="lazarus/fix")
pr_creator = PRCreator(config, Path.cwd())

# Check prerequisites
if pr_creator.is_gh_available() and pr_creator.is_gh_authenticated():
    result = pr_creator.create_pr(healing_result, script_path)
    print(f"PR: {result.pr_url}")
```

### Common Commands
```bash
# Heal with PR creation
lazarus heal scripts/failing.py

# Monitor and auto-heal
lazarus monitor --config lazarus.yaml

# Check PR status
gh pr list --head lazarus/fix/failing

# View PR details
gh pr view 123
```

## Support

- **Documentation**: `docs/git-integration.md`
- **Examples**: `examples/pr_creation_example.py`
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Summary

You're now ready to use Lazarus PR creation:

✅ GitHub CLI installed and authenticated
✅ Configuration file updated
✅ Prerequisites verified
✅ First healing with PR ready to run

Start healing with automatic PR creation:
```bash
lazarus heal your-script.py
```
