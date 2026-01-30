# Examples

Practical demonstrations of Lazarus healing different types of script failures.

## Quick Navigation

- [Example Scenarios](#example-scenarios)
- [Running Examples](#running-examples)
- [Example Details](#example-details)
- [Learning Path](#learning-path)

---

## Example Scenarios

Lazarus includes 6 complete example scenarios demonstrating various failure types:

| Name | Scenario | Difficulty | Time |
|------|----------|-----------|------|
| [python-syntax-error](#1-python-syntax-error) | Missing colon in function definition | Easy | 5 min |
| [shell-typo](#2-shell-typo) | Command typos in shell script | Easy | 5 min |
| [nodejs-runtime-error](#3-nodejs-runtime-error) | Calling undefined JavaScript function | Medium | 10 min |
| [api-change-simulation](#4-api-change-simulation) | Adapting to breaking API changes | Medium | 15 min |
| [multi-file-fix](#5-multi-file-fix) | Bugs spanning multiple files | Hard | 15 min |
| [unfixable-scenario](#6-unfixable-scenario) | External dependencies (unfixable) | N/A | 10 min |

---

## Running Examples

### Prerequisites

```bash
# Ensure you have:
python3 --version  # 3.11+
node --version     # 18+ (for nodejs example)
lazarus --version  # Installed
claude --version   # CLI authenticated
gh auth status     # GitHub CLI authenticated
```

### Running Without Lazarus (See the Failure)

```bash
cd /Users/boris/work/personal/lazarus/examples/python-syntax-error
python3 script.py  # Fails with SyntaxError
```

### Running With Lazarus (Auto-Healing)

```bash
cd /Users/boris/work/personal/lazarus/examples/python-syntax-error
lazarus run ./script.py
# Lazarus will detect, fix, verify, and create a PR
```

---

## Example Details

### 1. Python Syntax Error

**Location:** `examples/python-syntax-error/`

**The Bug:**
A Python script with a missing colon in a function definition (line 12):
```python
def calculate_total_sales(sales_data)  # Missing colon
    return sum(sales_data.values())
```

**What It Teaches:**
- Basic Python syntax error detection
- Understanding SyntaxError messages
- One-line fixes in Python

**To Run:**
```bash
cd examples/python-syntax-error
# Without Lazarus (see failure):
python3 script.py

# With Lazarus (auto-healing):
lazarus run ./script.py
```

**Real-World Use:** Typos introduced during quick edits or copy-pasting code

---

### 2. Shell Typo

**Location:** `examples/shell-typo/`

**The Bugs:**
A shell script with command typos:
- Line 10: `echoo` (should be `echo`)
- Line 12: `mkdri` (should be `mkdir`)

**What It Teaches:**
- Shell script error detection
- Multiple related fixes in one pass
- "command not found" error handling

**To Run:**
```bash
cd examples/shell-typo
# Without Lazarus (see failure):
./backup.sh

# With Lazarus (auto-healing):
lazarus run ./backup.sh
```

**Real-World Use:** Scheduled backup scripts that fail due to typos

---

### 3. Node.js Runtime Error

**Location:** `examples/nodejs-runtime-error/`

**The Bug:**
JavaScript code calling an undefined function (line 38):
```javascript
const user = getUserById(1);  // getUserById is not defined
```

**What It Teaches:**
- JavaScript runtime errors vs syntax errors
- Stack trace analysis
- Function implementation from context
- Cross-language support in Lazarus

**To Run:**
```bash
cd examples/nodejs-runtime-error
# Without Lazarus (see failure):
node app.js

# With Lazarus (auto-healing):
lazarus run ./app.js
```

**Real-World Use:** Scripts broken by incomplete refactoring or removed functions

---

### 4. API Change Simulation

**Location:** `examples/api-change-simulation/`

**The Bug:**
Code using outdated function signature. The `api_module.py` changed `get_user_data()` to require a new `format` parameter, but `fetch_data.py` hasn't been updated:
```python
user_data = get_user_data(user_id)  # Missing new required parameter
# Should be: get_user_data(user_id, format='json')
```

**What It Teaches:**
- Breaking API changes in dependencies
- Function signature migration
- Real-world maintenance scenarios
- Dependency version upgrade handling

**To Run:**
```bash
cd examples/api-change-simulation
# Without Lazarus (see failure):
python3 fetch_data.py

# With Lazarus (auto-healing):
lazarus run ./fetch_data.py
```

**Real-World Use:** When a library releases breaking changes (pip, npm package updates)

---

### 5. Multi-File Fix

**Location:** `examples/multi-file-fix/`

**The Bugs:**
Bugs spanning multiple files in a package:
- `utils/helpers.py` line 18: Division by zero (no empty list check)
- `utils/helpers.py` line 39: Missing `$` in currency formatting

**What It Teaches:**
- Fixing bugs spanning multiple files
- Cross-file dependency analysis
- Utility library debugging
- Comprehensive code healing

**To Run:**
```bash
cd examples/multi-file-fix
# Without Lazarus (see failure):
python3 main.py

# With Lazarus (auto-healing):
lazarus run ./main.py
```

**Real-World Use:** Bugs in shared utility libraries affecting multiple scripts

---

### 6. Unfixable Scenario

**Location:** `examples/unfixable-scenario/`

**The Issues:**
A script with external dependencies that cannot be fixed by modifying code:
- Missing config file: `/etc/myapp/production.conf`
- Unreachable service: `production-db.internal.company.com:5432`
- Missing credentials: `SECRET_API_KEY` environment variable

**What It Teaches:**
- Understanding Lazarus limitations
- When manual intervention is required
- Graceful failure handling
- Notification importance
- Realistic expectations for automation

**To Run:**
```bash
cd examples/unfixable-scenario
# Without Lazarus (see failure):
python3 impossible.py

# With Lazarus (graceful failure):
lazarus run ./impossible.py
# Will show helpful error after 2 attempts
```

**Real-World Use:** Setting realistic expectations - not all failures can be auto-healed

---

## Learning Path

### Recommended Order

Follow this sequence to progressively learn Lazarus:

**1. Start Simple (5 minutes)**
```bash
cd examples/python-syntax-error
lazarus run ./script.py
# Observe: Simple syntax fix
```

**2. Cross Language (5 minutes)**
```bash
cd examples/shell-typo
lazarus run ./backup.sh
# Observe: Multiple fixes in one script
```

**3. Runtime Errors (10 minutes)**
```bash
cd examples/nodejs-runtime-error
lazarus run ./app.js
# Observe: Runtime vs syntax errors, function implementation
```

**4. Real-World Complexity (15 minutes)**
```bash
cd examples/api-change-simulation
lazarus run ./fetch_data.py
# Observe: Breaking API changes, signature updates
```

**5. Advanced: Multiple Files (15 minutes)**
```bash
cd examples/multi-file-fix
lazarus run ./main.py
# Observe: Cross-file fixes, comprehensive analysis
```

**6. Understanding Limits (10 minutes)**
```bash
cd examples/unfixable-scenario
lazarus run ./impossible.py
# Observe: When Lazarus can't help, graceful failure
```

**Total Time:** ~1 hour for complete understanding

---

## Understanding Example Structure

Each example directory contains:

```
example-name/
├── script files (*.py, *.sh, *.js)  # The failing code
├── lazarus.yaml                      # Lazarus configuration
├── README.md                         # Detailed explanation
└── supporting files                  # Dependencies (package.json, utils/, etc.)
```

### Configuration Patterns

**Basic Example:**
```yaml
version: "1"
scripts:
  - name: "my-script"
    path: "./script.py"

healing:
  max_attempts: 3
  timeout_per_attempt: 120
  allowed_files:
    - "script.py"

git:
  create_pr: true
  branch_prefix: "lazarus/fix"
```

**Multi-File Example:**
```yaml
healing:
  allowed_files:
    - "main.py"
    - "utils/helpers.py"
    - "utils/__init__.py"
```

**Limited Attempts (unfixable):**
```yaml
healing:
  max_attempts: 2          # Fewer attempts
  timeout_per_attempt: 60  # Shorter timeout

git:
  create_pr: false         # Don't create PR if unfixable
```

---

## Full Example Documentation

For detailed information about each example, including:
- Complete source code
- Expected behavior
- The fix explanation
- Learning objectives
- Real-world scenarios

See the individual README.md files in each example directory:
- `examples/python-syntax-error/README.md`
- `examples/shell-typo/README.md`
- `examples/nodejs-runtime-error/README.md`
- `examples/api-change-simulation/README.md`
- `examples/multi-file-fix/README.md`
- `examples/unfixable-scenario/README.md`

Also see `examples/README.md` for comprehensive documentation and `examples/QUICKSTART.md` for a 5-minute introduction.

---

## Next Steps

After exploring the examples:

1. **Configure your project** - Create your own `lazarus.yaml`
2. **Run on your scripts** - Use Lazarus on your failing scripts
3. **Review the PRs** - See how Claude Code fixes your code
4. **Customize settings** - Adjust healing parameters for your needs
5. **Integrate with CI/CD** - Set up automatic healing in your pipeline

See the [Getting Started Guide](getting-started.md) and [Configuration Reference](configuration.md) for more details.
