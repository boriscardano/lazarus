# Multi-File Fix Example

This example demonstrates Lazarus's ability to fix bugs that span multiple files in a codebase.

## The Bugs

This example has TWO bugs in different files:

### Bug 1: Division by Zero in `utils/helpers.py` (line 18)
```python
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)  # No check for empty list!
```

### Bug 2: Missing Dollar Sign in `utils/helpers.py` (line 39)
```python
def format_currency(amount):
    return f"{amount:,.2f}"  # Missing '$' prefix
```

The `main.py` script uses both of these helper functions, and the first bug causes a crash.

## Expected Behavior

When working correctly, the script should:
1. Generate a sales report with totals and averages
2. Show sales breakdown by product
3. Handle edge cases like empty lists gracefully
4. Format all currency values with dollar signs

## Running This Example

### Without Lazarus (will fail)

```bash
cd examples/multi-file-fix
python3 main.py
```

You'll see output like:
```
Sales Report Generator v1.0

==================================================
SALES REPORT
==================================================

Total Sales: 641.25      # BUG: Missing $ sign
Average Sale: 128.25     # BUG: Missing $ sign
Number of Transactions: 5

Sales by Product:
  Widget A:
    Total: 350.00        # BUG: Missing $ sign
    Average: 175.00      # BUG: Missing $ sign
    Count: 2
  ...

==================================================
TESTING EDGE CASE
==================================================

Calculating average for empty sales list...
Traceback (most recent call last):
  File "main.py", line 80, in <module>
    main()
  File "main.py", line 74, in main
    empty_average = calculate_average([])
  File "utils/helpers.py", line 18, in calculate_average
    return total / len(numbers)
ZeroDivisionError: division by zero
```

### With Lazarus (auto-healing)

```bash
cd examples/multi-file-fix
lazarus run ./main.py
```

Lazarus will:
1. Detect the ZeroDivisionError
2. Analyze the stack trace across files
3. Identify the bug in `utils/helpers.py`
4. Also notice the missing dollar sign in currency formatting
5. Fix both bugs in `utils/helpers.py`
6. Re-run the script to verify all fixes work
7. Create a PR showing changes to multiple files

## Expected Fixes

### Fix 1: Add empty list check
```python
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    total = sum(numbers)
    return total / len(numbers)
```

### Fix 2: Add dollar sign
```python
def format_currency(amount):
    """Format a number as currency (USD)."""
    return f"${amount:,.2f}"
```

## Learning Points

### Multi-File Bugs Are Common

In real projects, bugs often span multiple files because:
- **Utility libraries**: Helper functions used across the codebase
- **Class hierarchies**: Base class bug affects all subclasses
- **Imports and dependencies**: Changes in one module break another
- **Interface contracts**: Function signatures don't match expectations

### Why Multi-File Fixes Are Hard

Without AI assistance:
- Must trace execution across file boundaries
- Need to understand relationships between modules
- Risk of missing related issues in other files
- Manual coordination of changes is error-prone

### How Lazarus Handles This

Lazarus can:
- **Trace execution**: Follow stack traces across multiple files
- **Understand context**: Analyze how functions are used in calling code
- **Fix comprehensively**: Update all related files in one healing session
- **Verify completely**: Test that all changes work together
- **Document clearly**: PR shows all changes with explanations

## Real-World Scenarios

This pattern is common in:

1. **Refactoring gone wrong**:
   - Updated a function signature in one file
   - Forgot to update callers in other files

2. **Shared utilities**:
   - Bug in a common helper function
   - Affects many scripts across the project

3. **Module migrations**:
   - Moving functions between files
   - Import statements need updating in multiple places

4. **Test failures**:
   - Test reveals bug in implementation
   - Both test and implementation need fixes

## Configuration Notes

The `lazarus.yaml` crucially includes:
```yaml
allowed_files:
  - "main.py"
  - "utils/helpers.py"
  - "utils/__init__.py"
```

This explicitly permits Lazarus to modify multiple files. Without this:
- Lazarus might only fix symptoms in the main script
- Root cause in helper module would remain
- Script might work around the bug instead of fixing it

## Testing the Fix Manually

After Lazarus fixes the code:

```bash
cd examples/multi-file-fix
python3 main.py
```

You should see:
```
Sales Report Generator v1.0

==================================================
SALES REPORT
==================================================

Total Sales: $641.25
Average Sale: $128.25
Number of Transactions: 5

Sales by Product:
  Widget A:
    Total: $350.00
    Average: $175.00
    Count: 2
  Widget B:
    Total: $165.50
    Average: $82.75
    Count: 2
  Widget C:
    Total: $125.75
    Average: $125.75
    Count: 1

==================================================
TESTING EDGE CASE
==================================================

Calculating average for empty sales list...
Average: $0.00

✓ Report generated successfully!
```

## Architecture Lesson

This example demonstrates **defense in depth**:
- The helper function should handle edge cases (empty lists)
- The calling code can also add validation
- Both layers working together prevent failures

Lazarus understands this and can fix issues at the appropriate layer.

## Fixed Version

Corrected versions of all files are available in the `fixed/` subdirectory.

**Location:**
- `fixed/main.py` (main script - minimal changes, comments updated)
- `fixed/utils/helpers.py` (both bugs fixed here)
- `fixed/utils/__init__.py` (updated to export calculate_total)

**What was fixed:**

1. **utils/helpers.py - calculate_average():**
   - Added check for empty list: `if not numbers: return 0.0`
   - Prevents ZeroDivisionError

2. **utils/helpers.py - format_currency():**
   - Changed return from `f"{amount:,.2f}"` to `f"${amount:,.2f}"`
   - Adds dollar sign prefix

3. **utils/__init__.py:**
   - Added `calculate_total` to imports and `__all__`

**To compare the broken vs fixed versions:**

```bash
# See differences in the helper module (where the bugs were)
diff utils/helpers.py fixed/utils/helpers.py

# Or use a side-by-side diff
diff -y utils/helpers.py fixed/utils/helpers.py

# Compare the __init__ file too
diff utils/__init__.py fixed/utils/__init__.py

# Run the fixed version
cd fixed
python3 main.py
```

**Expected output from the fixed version:**
```
Sales Report Generator v1.0

==================================================
SALES REPORT
==================================================

Total Sales: $641.25
Average Sale: $128.25
Number of Transactions: 5

Sales by Product:
  Widget A:
    Total: $350.00
    Average: $175.00
    Count: 2
  Widget B:
    Total: $165.50
    Average: $82.75
    Count: 2
  Widget C:
    Total: $125.75
    Average: $125.75
    Count: 1

==================================================
TESTING EDGE CASE
==================================================

Calculating average for empty sales list...
Average: $0.00

✓ Report generated successfully!
```
