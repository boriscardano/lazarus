# Lazarus Improvements & Feature Ideas

Compiled during comprehensive E2E testing on 2026-01-30.

## Bugs / Issues Found

### 1. Shell Script Healing Timeouts
- **Severity**: Medium
- **Description**: Shell scripts with typos (echoo, mkdri) cause Claude Code to timeout even with 180s per-attempt timeout
- **Impact**: Shell script healing may be unreliable
- **Suggested Fix**: Investigate why Claude Code takes so long for shell fixes; consider longer default timeouts or async handling

### 2. History Location Not Intuitive
- **Severity**: Low
- **Description**: `lazarus history` only works when run from the same directory as lazarus.yaml
- **Impact**: Users may think no history exists
- **Suggested Fix**: Add `--history-dir` flag or search parent directories for history

### 3. E2E Tests Always Skipped
- **Severity**: Low
- **Description**: E2E tests have hard-coded `@pytest.mark.skip` decorators, making `--run-e2e` flag ineffective
- **Impact**: Can't run automated E2E tests in CI
- **Suggested Fix**: Use conditional skip based on environment variable instead

## Feature Ideas

### High Priority

1. **Use `uv` instead of `pip`**
   - Modern, faster Python package manager
   - Better dependency resolution
   - Update install scripts and documentation

2. **Parallel Healing**
   - Allow healing multiple scripts simultaneously
   - Useful for batch failures
   - Could use asyncio or multiprocessing

3. **Better Timeout Handling**
   - Configurable timeouts per script type
   - Different defaults for Python vs Shell vs Node
   - Option to continue without timeout

4. **Retry with Different Model**
   - If first model fails, try a different Claude model
   - Configurable model fallback chain

### Medium Priority

5. **Web Dashboard**
   - View healing history visually
   - Statistics and charts
   - Success rate over time

6. **Healing Suggestions Without Auto-Fix**
   - `lazarus diagnose` command
   - Shows what Claude thinks is wrong without modifying files
   - Useful for review before healing

7. **Healing Cache/Learning**
   - Remember successful fixes for similar errors
   - Avoid repeated API calls for known issues
   - Local embedding-based similarity search

8. **Notification Templates**
   - Customizable notification message formats
   - Support for custom fields/variables
   - Per-script notification config

### Low Priority

9. **Git Stash Integration**
   - Better handling of uncommitted changes
   - Option to auto-stash before healing
   - Restore stash on failure

10. **Multiple Config Files**
    - Support for `lazarus.d/` directory
    - Include/extend configs
    - Environment-specific overrides

11. **Dry Run Improvements**
    - Show what Claude would do without modifying
    - Preview mode with diff output

12. **Homebrew Formula**
    - `brew install lazarus`
    - Easier macOS installation

## Test Coverage Improvements Needed

Modules with <70% coverage that need more tests:

| Module | Coverage | Priority |
|--------|----------|----------|
| core/runner.py | 12% | Critical |
| core/verification.py | 13% | Critical |
| logging/formatters.py | 12% | Medium |
| cli.py | 21% | High |
| core/healer.py | 48% | High |
| git/pr.py | 48% | Medium |
| config/loader.py | 54% | Medium |
| notifications/webhook.py | 55% | Low |

## Security Improvements Done (Polish Pass 3)

- ✅ SSRF protection for webhook URLs
- ✅ Branch name sanitization
- ✅ Input validation for private IPs

## Code Quality Improvements Done (Polish Passes 1-5)

- ✅ Fixed all test failures
- ✅ Standardized Optional[T] type hints
- ✅ Fixed import organization
- ✅ Removed TODO comments
- ✅ Fixed type annotation errors

## Performance Ideas

1. **Lazy Loading**
   - Don't load all modules on startup
   - Faster CLI response time

2. **Connection Pooling**
   - Reuse HTTP connections for notifications
   - Reduce latency for multiple notifications

3. **Incremental History**
   - Don't load all history on `lazarus history`
   - Pagination support

## Documentation Needed

1. Troubleshooting guide for common errors
2. Performance tuning guide
3. Best practices for writing healable scripts
4. CI/CD integration examples (beyond GitHub Actions)
