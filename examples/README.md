# Lazarus Examples

This directory contains example scripts demonstrating various failure scenarios that Lazarus can detect and heal automatically.

## Overview

Each example is self-contained and demonstrates a specific type of failure:

| Example | Failure Type | Difficulty | Learn About |
|---------|-------------|------------|-------------|
| [python-syntax-error](python-syntax-error/) | Syntax Error | Easy | Basic Python syntax fixes |
| [shell-typo](shell-typo/) | Command Typo | Easy | Shell command corrections |
| [nodejs-runtime-error](nodejs-runtime-error/) | Runtime Error | Medium | Missing function implementation |
| [api-change-simulation](api-change-simulation/) | API Breaking Change | Medium | Adapting to dependency changes |
| [multi-file-fix](multi-file-fix/) | Multi-file Bug | Hard | Cross-file bug fixes |
| [unfixable-scenario](unfixable-scenario/) | External Dependency | Impossible | Lazarus limitations |

## Quick Start

### Prerequisites

Before running the examples, make sure you have:
- Python 3.11+ installed
- Node.js 18+ (for the nodejs-runtime-error example)
- Lazarus installed (`pip install lazarus-heal`)
- Claude Code installed and authenticated
- Git and `gh` CLI (for PR creation)

### Running an Example

Each example can be run in two ways:

**Without Lazarus (to see the failure):**
```bash
cd examples/python-syntax-error
python3 script.py  # This will fail
```

**With Lazarus (auto-healing):**
```bash
cd examples/python-syntax-error
lazarus run ./script.py  # Lazarus will detect, fix, and verify
```

## Example Details

### 1. Python Syntax Error

**Location:** `python-syntax-error/`

**Bug:** Missing colon in function definition

**What you'll learn:**
- How Lazarus detects and fixes Python syntax errors
- Understanding Python's error messages
- Auto-fixing basic syntax mistakes

**Use case:** Common when copy-pasting code or refactoring quickly

### 2. Shell Script Typo

**Location:** `shell-typo/`

**Bugs:** Command typos (`echoo`, `mkdri`)

**What you'll learn:**
- Fixing "command not found" errors
- Shell command auto-correction
- Handling multiple typos in one script

**Use case:** Scheduled backup scripts that fail due to typos

### 3. Node.js Runtime Error

**Location:** `nodejs-runtime-error/`

**Bug:** Calling undefined function

**What you'll learn:**
- Fixing JavaScript runtime errors
- Implementing missing functions
- Understanding call stack analysis

**Use case:** Scripts broken by incomplete refactoring

### 4. API Change Simulation

**Location:** `api-change-simulation/`

**Bug:** Calling function with outdated signature

**What you'll learn:**
- Adapting to breaking API changes
- Updating function calls across codebase
- Managing dependency version upgrades

**Use case:** When a library releases breaking changes

### 5. Multi-File Fix

**Location:** `multi-file-fix/`

**Bugs:** Division by zero + missing formatting in helper module

**What you'll learn:**
- Fixing bugs that span multiple files
- Understanding cross-file dependencies
- Comprehensive code analysis

**Use case:** Bugs in shared utility libraries

### 6. Unfixable Scenario

**Location:** `unfixable-scenario/`

**Issues:** Missing config files, unreachable services, missing credentials

**What you'll learn:**
- Understanding Lazarus's limits
- What requires manual intervention
- Graceful failure handling
- Proper notification strategies

**Use case:** Setting realistic expectations for automation

## Running All Examples

You can test all examples sequentially:

```bash
# Create a test script
cat > /tmp/test_all_examples.sh << 'EOF'
#!/bin/bash

EXAMPLES_DIR="/Users/boris/work/personal/lazarus/examples"
RESULTS_LOG="/tmp/lazarus_examples_results.log"

echo "Testing Lazarus Examples" > "$RESULTS_LOG"
echo "=========================" >> "$RESULTS_LOG"
echo "" >> "$RESULTS_LOG"

for example in python-syntax-error shell-typo nodejs-runtime-error api-change-simulation multi-file-fix unfixable-scenario; do
    echo "Testing: $example" | tee -a "$RESULTS_LOG"
    cd "$EXAMPLES_DIR/$example" || continue

    # Run with Lazarus
    lazarus run ./*.py ./*.sh ./*.js 2>&1 | tee -a "$RESULTS_LOG"

    echo "---" >> "$RESULTS_LOG"
    echo "" >> "$RESULTS_LOG"
done

echo "Results saved to: $RESULTS_LOG"
EOF

chmod +x /tmp/test_all_examples.sh
/tmp/test_all_examples.sh
```

## Understanding the Examples

### Anatomy of Each Example

Every example directory contains:

1. **Script file(s)** - The failing script(s)
2. **lazarus.yaml** - Configuration for healing
3. **README.md** - Detailed explanation of the bug and fix
4. **Additional files** - Dependencies (package.json, helper modules, etc.)

### Configuration Patterns

Each `lazarus.yaml` demonstrates different configuration patterns:

```yaml
# Basic configuration
version: "1"
scripts:
  - name: "my-script"
    path: "./script.py"

healing:
  max_attempts: 3
  timeout_per_attempt: 120
  allowed_files:
    - "script.py"  # Explicitly list modifiable files

git:
  create_pr: true
  branch_prefix: "lazarus/fix"
```

### Learning Path

**Recommended order for learning:**

1. Start with `python-syntax-error` - Simplest case
2. Try `shell-typo` - Different language, similar concept
3. Explore `nodejs-runtime-error` - Runtime vs syntax errors
4. Study `api-change-simulation` - Real-world complexity
5. Examine `multi-file-fix` - Advanced cross-file fixes
6. Finish with `unfixable-scenario` - Understanding limits

## Extending the Examples

### Creating Your Own Examples

To create a new example:

1. **Create the directory:**
   ```bash
   mkdir -p examples/my-new-example
   cd examples/my-new-example
   ```

2. **Create a failing script:**
   ```bash
   # Add your script with a clear, fixable bug
   ```

3. **Add configuration:**
   ```bash
   lazarus init  # Generate template
   # Edit lazarus.yaml to customize
   ```

4. **Document it:**
   ```bash
   # Create README.md explaining:
   # - The bug
   # - Expected behavior
   # - What Lazarus will do
   # - Learning points
   ```

### Example Ideas

More examples you could create:

- **Python import error** - Missing or wrong imports
- **Environment variable** - Script expects env vars
- **File permission** - Script can't read/write files
- **Dependency version** - Wrong package version
- **Configuration error** - Invalid config format
- **Race condition** - Timing-dependent failure
- **Memory leak** - Resource exhaustion
- **Infinite loop** - Timeout-based detection

## Testing & Validation

### Manual Testing

For each example:

1. **Test the failure:**
   ```bash
   cd examples/<example-name>
   # Run script directly (should fail)
   ```

2. **Test Lazarus healing:**
   ```bash
   lazarus run ./script.*
   # Should detect, fix, verify
   ```

3. **Check the PR:**
   ```bash
   gh pr list
   # Review the auto-generated PR
   ```

### Automated Testing

Run the example test suite:

```bash
# From project root
pytest tests/test_examples.py
```

This will:
- Verify each example fails as expected
- Test that Lazarus can fix each example (except unfixable)
- Validate the generated PRs
- Check notification delivery

## Common Issues

### Example Won't Run

**Problem:** Script fails to execute

**Solutions:**
- Check file permissions: `chmod +x script.*`
- Verify dependencies: `pip install -r requirements.txt`
- Check Python/Node version: `python3 --version`, `node --version`

### Lazarus Can't Fix

**Problem:** Healing fails repeatedly

**Check:**
- Is the example in the "unfixable" category?
- Are the `allowed_files` configured correctly?
- Is Claude Code authenticated?
- Check logs: `lazarus history`

### PR Not Created

**Problem:** No PR appears after healing

**Check:**
- Is git configured: `git config user.name`
- Is `gh` CLI authenticated: `gh auth status`
- Check `lazarus.yaml` has `create_pr: true`
- Are you in a git repository?

## Best Practices

### When Creating Examples

1. **Keep bugs simple** - One clear issue per example
2. **Make them realistic** - Based on real-world scenarios
3. **Document thoroughly** - Explain why and how
4. **Test both paths** - Verify failure and fix
5. **Include learning points** - What should users take away?

### When Using Examples

1. **Read the README first** - Understand what to expect
2. **Try failing first** - See the error before the fix
3. **Watch Lazarus work** - Observe the healing process
4. **Review the PR** - Learn from the AI's approach
5. **Experiment** - Modify examples to test edge cases

## Contributing Examples

Have an interesting failure scenario? Contribute it!

1. Fork the repository
2. Create your example in `examples/`
3. Follow the structure of existing examples
4. Write clear documentation
5. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

## Additional Resources

- [Lazarus Documentation](../docs/)
- [Configuration Reference](../docs/configuration.md)
- [Architecture Guide](../docs/architecture.md)
- [Troubleshooting](../docs/troubleshooting.md)
- [FAQ](../docs/faq.md)

## Support

Questions about the examples?

- Open an issue on GitHub
- Check the [FAQ](../docs/faq.md)
- Join our Discord community
- Email: support@lazarus-heal.dev

---

**Remember:** These examples are teaching tools. Real-world scenarios may be more complex, but the principles are the same!
