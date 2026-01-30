# Unfixable Scenario Example

This example demonstrates the **limits** of what Lazarus can auto-fix. It shows realistic scenarios that require manual intervention.

## Why This Example Matters

It's important to understand what Lazarus CAN'T fix:
- Setting realistic expectations
- Designing better notification strategies
- Understanding when manual intervention is needed
- Showing graceful failure handling

## The Unfixable Issues

The `impossible.py` script has three types of problems that can't be auto-fixed:

### 1. Missing External File (line 19-25)
```python
config_path = "/etc/myapp/production.conf"
with open(config_path, 'r') as f:
    config = f.read()
```

**Why unfixable:**
- File doesn't exist and Lazarus doesn't know what content it should have
- Requires sudo/root access to create in `/etc/`
- Content is application-specific and unknown to AI
- Could contain sensitive information or complex formatting

### 2. Unreachable Network Service (line 29-49)
```python
db_host = "production-db.internal.company.com"
sock.connect((db_host, db_port))
```

**Why unfixable:**
- Database server might be down
- Network connectivity issues
- DNS resolution failures
- Firewall blocking the connection
- Service on wrong host/port

### 3. Missing Credentials (line 53-68)
```python
api_key = os.environ.get('SECRET_API_KEY')
if not api_key:
    raise ValueError("Missing SECRET_API_KEY...")
```

**Why unfixable:**
- API keys must be obtained through proper channels
- Security implications - can't auto-generate credentials
- May require account creation, payment, approval processes
- Environment variables are external to the script

## Expected Behavior

### Without Lazarus (immediate failure)

```bash
cd examples/unfixable-scenario
python3 impossible.py
```

Output:
```
============================================================
UNFIXABLE SCENARIO DEMONSTRATION
============================================================

This script requires external resources that are missing:
1. Configuration file at /etc/myapp/production.conf
2. Database server running at production-db.internal.company.com
3. SECRET_API_KEY environment variable

Lazarus cannot auto-fix these issues because they require:
- Manual file creation with specific content
- External services to be running
- Credentials that must be obtained securely

------------------------------------------------------------

Reading configuration from /etc/myapp/production.conf...
ERROR: [Errno 2] No such file or directory: '/etc/myapp/production.conf'
→ This requires manual creation of the config file
```

### With Lazarus (graceful failure)

```bash
cd examples/unfixable-scenario
lazarus run ./impossible.py
```

Lazarus will:
1. Detect the failure (missing file)
2. Analyze the error and code
3. Recognize this requires external resources
4. Try to create a workaround (likely fail after 2 attempts)
5. Report the failure with clear explanation
6. NOT create a PR (configured with `create_pr: false`)
7. Send notifications if configured

Example Lazarus output:
```
[Lazarus] Script failed with exit code 1
[Lazarus] Error: FileNotFoundError: /etc/myapp/production.conf
[Lazarus] Analyzing failure...
[Lazarus] This failure requires external resources:
[Lazarus]   - Missing configuration file
[Lazarus]   - Requires manual creation at /etc/myapp/production.conf
[Lazarus] Attempting healing (1/2)...
[Lazarus] Unable to auto-fix: External dependency
[Lazarus] Attempting healing (2/2)...
[Lazarus] Unable to auto-fix: External dependency
[Lazarus] ✗ Healing failed after 2 attempts
[Lazarus] Manual intervention required
[Lazarus] Notification sent to configured channels
```

## What Lazarus Will Try (and Why It Fails)

Lazarus might attempt:

1. **Workaround attempts:**
   - Try using a different file path (user directory instead of `/etc/`)
   - Add try/except to handle the missing file gracefully
   - Create a default config file in the script's directory

2. **Why these fail:**
   - Script logic requires the specific file location
   - Default config doesn't have the right structure/values
   - Changes would alter the script's intended behavior too much

3. **Graceful degradation:**
   - Lazarus might add better error messages
   - Could add config file path checking with helpful hints
   - But ultimately can't make the script succeed

## Learning Points

### What Makes Issues Unfixable?

1. **External Dependencies:**
   - Files that must exist outside the codebase
   - Network services that must be running
   - Environment variables from external systems

2. **Unknown Information:**
   - Specific configuration values
   - Credentials and API keys
   - Business logic not in the code

3. **Permissions Issues:**
   - Files requiring root/admin access
   - Protected resources
   - Restricted network access

4. **Infrastructure Problems:**
   - Server downtime
   - Network connectivity
   - DNS resolution
   - Cloud service issues

### Designing for Lazarus

When writing scripts that Lazarus will monitor:

**Good patterns (fixable):**
```python
# Clear logic errors
def calculate_total(items):
    return sum(items)  # Works

# Obvious typos
command = "mkdri"  # Should be mkdir

# Missing imports
from math import sqrt  # If missing, Lazarus can add
```

**Unfixable patterns:**
```python
# External dependencies
config = load_from_s3("s3://bucket/config.json")

# Unknown credentials
api = APIClient(token=get_token_from_vault())

# Infrastructure
db = connect(host="prod-db-1.private.aws")
```

**Better approach:**
```python
# Make dependencies explicit with helpful errors
config_path = os.getenv('CONFIG_PATH')
if not config_path:
    raise ValueError(
        "CONFIG_PATH environment variable required. "
        "Set it to the path of your config file."
    )

# Document what's needed
# This script requires:
# 1. PostgreSQL running on localhost:5432
# 2. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY set
# 3. config.json in current directory
```

## Configuration Notes

The `lazarus.yaml` for this example:
- `max_attempts: 2` - Don't waste time on unfixable issues
- `create_pr: false` - Manual investigation needed
- `timeout_per_attempt: 60` - Short timeout since it will fail quickly

## Real-World Response

When Lazarus can't fix something:

1. **Notification sent** with error details
2. **No PR created** (to avoid noise)
3. **History logged** for tracking
4. **On-call engineer notified** via configured channels

The notification should include:
- What failed
- Why it couldn't be auto-fixed
- What manual steps are needed
- Relevant logs and error messages

## Success Metrics

For unfixable scenarios:
- **Fast failure detection** (within seconds)
- **Clear error reporting** (what's wrong and why)
- **Appropriate notifications** (right people, right channels)
- **No wasted healing attempts** (recognize futility quickly)
- **Actionable information** (what to do manually)

## Testing This Example

You can test Lazarus's limits:

```bash
cd examples/unfixable-scenario

# Run directly (will fail fast)
python3 impossible.py

# Run with Lazarus (will fail gracefully)
lazarus run ./impossible.py

# Check Lazarus history
lazarus history

# You should see:
# - Failure recorded
# - Reason: External dependency
# - Status: Unfixable
# - Recommendation: Manual intervention
```

## Philosophical Note

Good tools know their limits. Lazarus is designed to:
- **Fix what it can** (code logic, typos, API changes)
- **Recognize what it can't** (external resources, credentials)
- **Fail gracefully** (clear messages, appropriate notifications)
- **Learn over time** (patterns of what works vs. doesn't)

This makes Lazarus a reliable tool rather than one that attempts impossible fixes or gives false confidence.

## Fixed Version

The `fixed/` subdirectory contains a **README explaining why this scenario can't be auto-fixed** and what manual steps are required.

**Location:** `fixed/README.md`

This is intentionally NOT a fixed script, but rather documentation explaining:
- Why each issue is unfixable
- What manual steps are needed
- How to design scripts to be more fixable
- Alternative approaches (mocking, graceful degradation)
- Best practices for handling external dependencies

**To read the manual fix guide:**

```bash
# View the guide
cat fixed/README.md

# Or in a pager
less fixed/README.md

# Or in your editor
code fixed/README.md
```

The guide includes:
- Detailed explanation of each unfixable issue
- Specific commands to manually resolve them
- Alternative mock implementation for testing
- Design recommendations for Lazarus-friendly scripts
- When to notify vs. attempt auto-fix
