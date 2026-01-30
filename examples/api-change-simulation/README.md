# API Change Simulation Example

This example simulates a real-world scenario where a dependency's API changes, breaking your code.

## The Scenario

The `api_module.py` represents a third-party library that released a breaking change:

**Version 1.0** (old):
```python
def get_user_data(user_id):
    ...
```

**Version 2.0** (new):
```python
def get_user_data(user_id, include_metadata=False):
    ...
```

The script `fetch_data.py` was written for v1.0 and calls the function with the old signature:
```python
user = get_user_data(user_id)  # Missing: include_metadata parameter
```

## The Bug

Line 18 in `fetch_data.py` calls `get_user_data()` without the new required parameter. While the parameter has a default value, this example simulates real breaking changes where:
- Parameters are reordered
- Required parameters are added
- Return types change
- Functions are renamed or removed

## Expected Behavior

When working correctly, the script should:
1. Fetch individual user data for users 42 and 123
2. Display user information (ID, name, email, status)
3. List the first 5 users
4. Complete successfully

## Running This Example

### Without Lazarus (may work but doesn't use API correctly)

```bash
cd examples/api-change-simulation
python3 fetch_data.py
```

The script will run but won't use the API's new features properly. In a real breaking change, you'd see errors like:
```
TypeError: get_user_data() missing 1 required positional argument: 'include_metadata'
```

### With Lazarus (auto-adaptation)

```bash
cd examples/api-change-simulation
lazarus run ./fetch_data.py
```

Lazarus will:
1. Detect any TypeError or usage issues
2. Analyze both the caller and the API module
3. Understand the new API signature
4. Update all calls to `get_user_data()` to include the new parameter
5. Verify the script works with the updated API
6. Create a PR with the migration changes

## Expected Fix

The fix should update the function call to:

```python
# Option 1: Use default
user = get_user_data(user_id, include_metadata=False)

# Option 2: Enable metadata
user = get_user_data(user_id, include_metadata=True)
```

## Learning Points

### API Breaking Changes Are Common

In real projects, this happens when:
- **Dependencies update**: npm, pip, gems with major version bumps
- **Internal libraries evolve**: Your team's shared libraries change
- **Framework migrations**: Moving from Flask to FastAPI, React 17 to 18, etc.
- **Cloud service updates**: AWS, GCP APIs deprecate old endpoints

### Why This Is Hard

- Changes can affect many files across a codebase
- Documentation may be incomplete or unclear
- Deprecation warnings are often ignored
- Migration can be time-consuming

### How Lazarus Helps

Lazarus can:
- **Detect** when API signatures change
- **Analyze** the new requirements by reading source code or docs
- **Update** all call sites to use new signatures
- **Verify** changes work correctly
- **Document** what changed in the PR

## Real-World Example

Imagine you have 50 scheduled scripts running hourly. A dependency releases a major version update with breaking changes. Without Lazarus:
- Scripts start failing
- You get paged at 2 AM
- Manual debugging and fixes take hours
- Risk of missing some call sites

With Lazarus:
- First failure triggers auto-healing
- AI analyzes the API change
- All call sites are updated automatically
- PR is ready for review by morning
- You check the PR over coffee ☕

## Configuration Notes

The `lazarus.yaml` specifies:
- `allowed_files: ["fetch_data.py"]` - Only update the caller, not the library
- This is intentional - you typically can't modify third-party libraries
- The fix should adapt your code to the new API, not revert the library

## Fixed Version

Corrected versions of both files are available in the `fixed/` subdirectory.

**Location:**
- `fixed/api_module.py` (same as original - the API doesn't need fixing)
- `fixed/fetch_data.py` (updated to use the new API signature)

**What was fixed:**
- Line 19 in `fetch_data.py`: Added `include_metadata=False` parameter to `get_user_data()` call
- Now properly calls the API with the new signature

**To compare the broken vs fixed versions:**

```bash
# See the differences in the caller
diff fetch_data.py fixed/fetch_data.py

# Or use a side-by-side diff
diff -y fetch_data.py fixed/fetch_data.py

# Run the fixed version (need to update Python path)
cd fixed
python3 fetch_data.py
```

## Testing the Fix Manually

After Lazarus fixes the code, you can verify:

```bash
cd examples/api-change-simulation/fixed
python3 fetch_data.py
```

You should see:
```
User Data Fetcher v1.0
========================================

Fetching user 42...
User ID: 42
Name: User 42
Email: user42@example.com
Status: active

Fetching user 123...
User ID: 123
Name: User 123
Email: user123@example.com
Status: active

Fetching user list...
Found 5 users
  - User 1 (user1@example.com)
  - User 2 (user2@example.com)
  - User 3 (user3@example.com)
  - User 4 (user4@example.com)
  - User 5 (user5@example.com)

✓ Data fetch completed successfully!
```
