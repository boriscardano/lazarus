# Git Branch and PR Integration - Implementation Summary

## Overview
Integrated feature branch and PR creation into the Lazarus healer workflow. The healer now automatically:
1. Stashes uncommitted changes before healing
2. Creates a feature branch for fixes
3. Commits all healing changes to that branch
4. Pushes the branch and creates a PR (if configured)
5. Returns to the original branch and restores stashed changes

## Files Modified

### 1. `/src/lazarus/git/operations.py`
**Added Methods:**
- `stash_changes(message: Optional[str] = None) -> bool` - Stash uncommitted changes
- `pop_stash() -> bool` - Pop the most recent stash
- `has_stash() -> bool` - Check if there are stashed changes

**Location:** After the `get_remote_url` method (line ~389)

### 2. `/src/lazarus/core/healer.py`
**Major Changes:**

#### Imports (lines 10-31):
```python
import logging  # Added
from lazarus.git.operations import GitOperations, GitOperationError  # Added
from lazarus.git.pr import PRCreator  # Added

logger = logging.getLogger(__name__)  # Added
```

#### `__init__` method (lines 90-117):
- Added `repo_path: Optional[Path] = None` parameter
- Initialize `self.git_ops: Optional[GitOperations]` for git operations
- Auto-detect git repository if not specified

####  `heal` method (lines 119-309):
**Complete rewrite with git workflow integration:**

**Git Setup Phase:**
1. Stash uncommitted changes if present
2. Create and checkout feature branch with pattern: `{prefix}-{script-name}-{timestamp}`

**Healing Phase:**
- Run the existing healing logic (unchanged core flow)
- All Claude Code commits go to the feature branch automatically

**Finalization Phase:**
- Call `_finalize_healing` to handle git cleanup and PR creation
- Wrapped in try/except for emergency cleanup on errors

#### New Methods Added:

**`_finalize_healing` (add after `_enhance_context_for_retry`):**
```python
def _finalize_healing(
    self,
    result: HealingResult,
    script_path: Path,
    original_branch: Optional[str],
    stashed_changes: bool,
    feature_branch: Optional[str],
    has_changes: bool,
) -> HealingResult:
    """Finalize the healing process with git operations.

    This handles:
    - Pushing changes to remote (if any were made)
    - Creating a PR (if healing was successful and config enabled)
    - Returning to original branch
    - Restoring stashed changes
    """
```

**Implementation:**
1. Push feature branch to origin if changes were made
2. Create PR if:
   - Healing was successful
   - Changes were made
   - `config.git.create_pr` is True
3. Push branch even if healing failed (for debugging)
4. Always return to original branch (in finally block)
5. Always restore stashed changes (in finally block)
6. Handle all git errors gracefully without crashing healing

**`_generate_branch_name` (add after `_finalize_healing`):**
```python
def _generate_branch_name(self, script_path: Path) -> str:
    """Generate a feature branch name for healing.

    Uses pattern: {prefix}-{script-name}-{timestamp}
    Example: lazarus/fix-backup-20260130-143052
    """
```

## Error Handling

### Git Operations
- All git operations wrapped in try/except
- Failures logged but don't crash the healing process
- User warnings added to `result.error_message` when critical operations fail

### PR Creation
- If PR creation fails, healing result still returned as success (if healing worked)
- PR creation error logged and noted in result

### Emergency Cleanup
- Top-level try/except in `heal` method
- If any exception occurs, attempts to:
  1. Checkout original branch
  2. Pop stashed changes
- Then re-raises the exception

## Configuration

Uses existing `GitConfig` from `/src/lazarus/config/schema.py`:
- `create_pr: bool` - Whether to create PRs automatically (default: True)
- `branch_prefix: str` - Prefix for healing branches (default: "lazarus/fix")
- `draft_pr: bool` - Create PRs as drafts (default: False)
- Plus PR templates and other settings

## Testing Considerations

### Unit Tests to Update:
- `/tests/unit/test_healer.py` - Mock `GitOperations` and `PRCreator`
- Add tests for:
  - Stashing and unstashing workflow
  - Branch creation and checkout
  - PR creation on success
  - Branch push on failure (for debugging)
  - Emergency cleanup on exceptions
  - Graceful handling of git operation failures

### Integration Tests:
- Test full workflow with real git operations
- Test behavior when not in a git repository
- Test behavior when git operations fail

## Backward Compatibility

- `Healer.__init__` signature changed: added optional `repo_path` parameter
- Default behavior: auto-detect git repo (backward compatible)
- If not in git repo: healer works exactly as before (no git operations)
- Existing code calling `Healer(config)` will continue to work

## Usage Example

```python
from pathlib import Path
from lazarus.config.loader import load_config
from lazarus.core.healer import Healer

# Load configuration
config = load_config(Path("lazarus.toml"))

# Create healer (auto-detects git repo)
healer = Healer(config)

# Or specify repo path explicitly
healer = Healer(config, repo_path=Path("/path/to/repo"))

# Heal a script - now with automatic PR creation!
result = healer.heal(Path("scripts/backup.py"))

if result.success:
    print(f"Healed successfully in {len(result.attempts)} attempts")
    if result.pr_url:
        print(f"PR created: {result.pr_url}")
else:
    print(f"Healing failed: {result.error_message}")
```

## Git Workflow Summary

### Successful Healing:
```
1. Stash uncommitted changes (if any)
2. Create feature branch: lazarus/fix-script-name-timestamp
3. Checkout feature branch
4. Run healing attempts (Claude Code commits to this branch)
5. Push feature branch to origin
6. Create pull request
7. Checkout original branch
8. Pop stashed changes
9. Return result with PR URL
```

### Failed Healing:
```
1-4. Same as successful healing
5. Push feature branch to origin (for manual review)
6. Skip PR creation
7. Checkout original branch
8. Pop stashed changes
9. Return result with error message
```

### No Healing Needed (script already works):
```
1. Stash uncommitted changes (if any)
2. Create feature branch
3. Run script - it succeeds
4. Skip pushing (no changes made)
5. Skip PR creation
6. Checkout original branch
7. Pop stashed changes
8. Return success immediately
```

## Next Steps

1. Run tests to verify implementation:
   ```bash
   pytest tests/unit/test_healer.py -v
   pytest tests/unit/test_git_operations.py -v
   ```

2. Update CLI to pass `repo_path` to Healer if needed

3. Add end-to-end test for full git workflow

4. Update documentation with new workflow
