# Examples Quick Start Guide

Get up and running with Lazarus examples in 5 minutes.

## Prerequisites

```bash
# Check your environment
python3 --version  # Should be 3.11+
node --version     # Should be 18+
lazarus --version  # Should be installed
gh auth status     # Should be authenticated
```

## Try Your First Example

### 1. Python Syntax Error (Easiest)

```bash
cd examples/python-syntax-error

# See the failure
python3 script.py

# Watch Lazarus fix it
lazarus run ./script.py
```

**What happens:**
1. Script fails with "SyntaxError: invalid syntax"
2. Lazarus detects the missing colon
3. Adds `:` to line 11
4. Re-runs successfully
5. Creates PR with fix

### 2. Shell Script Typo

```bash
cd examples/shell-typo

# See the failure
./backup.sh

# Watch Lazarus fix it
lazarus run ./backup.sh
```

**What happens:**
1. Script fails with "command not found: echoo"
2. Lazarus identifies typos (`echoo` → `echo`, `mkdri` → `mkdir`)
3. Fixes both typos
4. Re-runs successfully
5. Creates PR

### 3. Node.js Runtime Error

```bash
cd examples/nodejs-runtime-error

# See the failure
node app.js

# Watch Lazarus fix it
lazarus run ./app.js
```

**What happens:**
1. Script fails with "ReferenceError: getUserById is not defined"
2. Lazarus analyzes the code and stack trace
3. Implements missing `getUserById` function
4. Re-runs successfully
5. Creates PR with new function

## Understanding Output

### When Script Fails

```
[Lazarus] Running script: ./script.py
[Lazarus] ✗ Script failed with exit code 1
[Lazarus] Error: SyntaxError: invalid syntax (line 11)
[Lazarus] Starting healing process...
```

### During Healing

```
[Lazarus] Attempt 1/3
[Lazarus] Analyzing failure context...
[Lazarus] Calling Claude Code for diagnosis...
[Lazarus] Fix proposed: Add missing colon to function definition
[Lazarus] Applying fix to script.py...
[Lazarus] Verifying fix...
```

### When Fix Succeeds

```
[Lazarus] ✓ Script executed successfully!
[Lazarus] Creating pull request...
[Lazarus] PR created: https://github.com/user/repo/pull/123
[Lazarus] Sending notifications...
[Lazarus] ✓ Healing completed successfully
```

## Next Steps

### Try More Examples

1. **API Change** - `cd examples/api-change-simulation`
2. **Multi-File Fix** - `cd examples/multi-file-fix`
3. **Unfixable** - `cd examples/unfixable-scenario` (see limits)

### Check the Results

```bash
# View healing history
lazarus history

# See created PRs
gh pr list

# Check specific PR
gh pr view 123
```

### Experiment

Modify the examples:
```bash
cd examples/python-syntax-error

# Make your own bugs
vi script.py

# Test Lazarus
lazarus run ./script.py
```

## Common Commands

```bash
# Run with auto-healing
lazarus run ./script.py

# Heal existing failing script
lazarus heal ./script.py

# Check Lazarus setup
lazarus check

# View configuration
cat lazarus.yaml

# Initialize new config
lazarus init
```

## Troubleshooting

### "Command not found: lazarus"

```bash
pip install lazarus-heal
# or
pip install -e /path/to/lazarus
```

### "Claude Code not authenticated"

```bash
claude auth login
```

### "gh not authenticated"

```bash
gh auth login
```

### "Permission denied"

```bash
chmod +x script.py
chmod +x backup.sh
chmod +x app.js
```

## Learning Path

Follow this order:

1. **python-syntax-error** (5 min) - Learn basics
2. **shell-typo** (5 min) - Different language
3. **nodejs-runtime-error** (10 min) - Runtime vs syntax
4. **api-change-simulation** (15 min) - Real-world scenario
5. **multi-file-fix** (15 min) - Complex fixes
6. **unfixable-scenario** (10 min) - Understanding limits

Total time: ~1 hour to complete all examples

## What You'll Learn

By the end of these examples, you'll understand:

- How Lazarus detects failures
- What types of bugs it can fix
- How it uses Claude Code for analysis
- When to use auto-healing vs manual fixes
- How to configure healing behavior
- What Lazarus can't fix (and why)

## Get Help

- Read the [Examples README](README.md)
- Check [Documentation](../docs/)
- Open an issue on GitHub
- Ask in Discord community

---

**Ready?** Start with `cd examples/python-syntax-error` and run `lazarus run ./script.py`!
