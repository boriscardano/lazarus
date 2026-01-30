# Python Syntax Error Example

This example demonstrates how Lazarus can automatically fix a common Python syntax error.

## The Bug

The script `script.py` has a **missing colon** on line 11:

```python
def calculate_total_sales(sales_data)  # Missing colon here!
    """Calculate the total sales from the data."""
```

This is a common mistake that prevents the script from even starting. When you run it, Python will immediately fail with a syntax error.

## Expected Behavior

When working correctly, the script should:
1. Process sample sales data
2. Calculate total sales and averages
3. Generate a JSON report with timestamp and statistics
4. Print the report to stdout

## Running This Example

### Without Lazarus (will fail)

```bash
cd examples/python-syntax-error
python3 script.py
```

You'll see an error like:
```
  File "script.py", line 11
    def calculate_total_sales(sales_data)  # Missing colon here!
                                          ^
SyntaxError: invalid syntax
```

### With Lazarus (auto-healing)

```bash
cd examples/python-syntax-error
lazarus run ./script.py
```

Lazarus will:
1. Detect the syntax error
2. Analyze the Python traceback
3. Identify the missing colon
4. Fix the code by adding `:` at the end of line 11
5. Re-run the script to verify the fix
6. Create a PR with the fix (if git is configured)

## Expected Fix

The fix should change line 11 to:

```python
def calculate_total_sales(sales_data):
    """Calculate the total sales from the data."""
```

## Learning Points

- **Syntax errors** are caught before runtime and are usually easy to fix
- Python's error messages are quite clear about the location and nature of syntax errors
- Lazarus can handle these automatically by analyzing the traceback
- This type of error is common when:
  - Copy-pasting code
  - Refactoring function signatures
  - Working late at night!

## Configuration Notes

The `lazarus.yaml` config specifies:
- `max_attempts: 3` - Allows up to 3 healing attempts
- `timeout_per_attempt: 120` - 2 minutes per attempt (syntax fixes are fast)
- `allowed_files: ["script.py"]` - Only allows modifying this one file

## Fixed Version

A corrected version of the script is available in the `fixed/` subdirectory. This shows what the healed code should look like after Lazarus fixes it.

**Location:** `fixed/script.py`

**What was fixed:**
- Line 12: Added the missing colon after the function definition

**To compare the broken vs fixed versions:**

```bash
# See the differences
diff script.py fixed/script.py

# Or use a side-by-side diff
diff -y script.py fixed/script.py

# Run the fixed version to see it work
python3 fixed/script.py
```

**Expected output from the fixed version:**
```
Processing sales data...

=== Sales Report ===
{
  "timestamp": "2024-12-15T10:30:00.123456",
  "total_sales": 641.25,
  "average_sale": 128.25,
  "num_transactions": 5
}

Report generated successfully!
```
