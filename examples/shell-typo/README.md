# Shell Script Typo Example

This example demonstrates how Lazarus can fix typos in shell commands that cause "command not found" errors.

## The Bugs

The script `backup.sh` has two typos:

1. **Line 8**: `echoo` instead of `echo`
   ```bash
   echoo "Starting backup process..."  # Typo!
   ```

2. **Line 12**: `mkdri` instead of `mkdir`
   ```bash
   mkdri -p "$BACKUP_DIR"  # Typo!
   ```

These are common typos that happen when typing quickly or when keys are mistyped.

## Expected Behavior

When working correctly, the script should:
1. Create a timestamped backup directory in `/tmp/`
2. Create sample source directories (data, config, logs)
3. Copy all source directories to the backup location
4. Print confirmation and list backup contents

## Running This Example

### Without Lazarus (will fail)

```bash
cd examples/shell-typo
./backup.sh
```

You'll see an error like:
```
./backup.sh: line 8: echoo: command not found
./backup.sh: line 9: echoo: command not found
./backup.sh: line 12: mkdri: command not found
```

The script will fail because these commands don't exist.

### With Lazarus (auto-healing)

```bash
cd examples/shell-typo
lazarus run ./backup.sh
```

Lazarus will:
1. Detect the "command not found" errors
2. Analyze the script and error messages
3. Identify that `echoo` should be `echo` and `mkdri` should be `mkdir`
4. Fix both typos in the script
5. Re-run to verify the backup works
6. Create a PR with the fixes

## Expected Fixes

The fixes should change:
- Line 8: `echoo` → `echo`
- Line 9: `echoo` → `echo`
- Line 12: `mkdri` → `mkdir`

## Learning Points

- **Command typos** are easy to make but cause immediate failures
- Shell error messages clearly indicate "command not found"
- Lazarus can identify common typos by:
  - Analyzing the command that failed
  - Looking for similar valid commands (edit distance)
  - Understanding the context (what the script is trying to do)
- Common typo patterns:
  - Double letters: `echoo`, `lss`, `cdd`
  - Missing letters: `mkdi`, `rmdi`, `ech`
  - Transposed letters: `sl` instead of `ls`

## Real-World Scenario

This type of error often happens when:
- Refactoring scripts quickly
- Copy-pasting from sources with typos
- Working in unfamiliar shells
- Scripts break after manual edits

Having Lazarus auto-fix these saves time, especially for scheduled maintenance scripts that might fail at 2 AM.

## Configuration Notes

The `lazarus.yaml` includes:
- `schedule: "0 2 * * *"` - Example of running this daily at 2 AM
- `timeout_per_attempt: 180` - 3 minutes per attempt
- `allowed_files: ["backup.sh"]` - Only the backup script can be modified

## Fixed Version

A corrected version of the script is available in the `fixed/` subdirectory.

**Location:** `fixed/backup.sh`

**What was fixed:**
- Lines 10-11: Changed `echoo` to `echo`
- Line 14: Changed `mkdri` to `mkdir`

**To compare the broken vs fixed versions:**

```bash
# See the differences
diff backup.sh fixed/backup.sh

# Or use a side-by-side diff
diff -y backup.sh fixed/backup.sh

# Run the fixed version
./fixed/backup.sh
```

**Expected output from the fixed version:**
```
Starting backup process...
Backup directory: /tmp/backup-20241215
Backing up ./data...
Backing up ./config...
Backing up ./logs...
Backup completed successfully!
Files backed up to: /tmp/backup-20241215
total 24
drwxr-xr-x  2 user  wheel   64 Dec 15 10:30 config
drwxr-xr-x  2 user  wheel   64 Dec 15 10:30 data
drwxr-xr-x  2 user  wheel   64 Dec 15 10:30 logs
```
