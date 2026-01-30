# Node.js Runtime Error Example

This example demonstrates how Lazarus can fix JavaScript runtime errors caused by undefined functions.

## The Bug

The script `app.js` calls a function that doesn't exist on line 38:

```javascript
const featuredUser = getUserById(1);  // This function is not defined!
```

The script runs fine until it reaches this line, then crashes with a `ReferenceError`.

## Expected Behavior

When working correctly, the script should:
1. Load user data from an array
2. Calculate statistics (total, active, inactive users)
3. Display the statistics
4. Show a featured user's details
5. Print success message

## Running This Example

### Without Lazarus (will fail)

```bash
cd examples/nodejs-runtime-error
node app.js
# or
npm start
```

You'll see an error like:
```
User Data Processor v1.0

Generating user report...

=== User Statistics ===
Total Users: 4
Active Users: 3
Inactive Users: 1

=== Featured User ===
ReferenceError: getUserById is not defined
    at generateReport (app.js:38:26)
    at main (app.js:46:5)
    at Object.<anonymous> (app.js:49:1)
```

### With Lazarus (auto-healing)

```bash
cd examples/nodejs-runtime-error
lazarus run ./app.js
```

Lazarus will:
1. Detect the ReferenceError
2. Analyze the stack trace and code
3. Identify that `getUserById` function is missing
4. Implement the missing function (finding a user by ID)
5. Re-run the script to verify it works
6. Create a PR with the fix

## Expected Fix

The fix should add a `getUserById` function, something like:

```javascript
function getUserById(id) {
    return users.find(u => u.id === id);
}
```

This should be added before the `generateReport` function (around line 24).

## Learning Points

- **Runtime errors** only occur when code is actually executed
- JavaScript's dynamic nature means missing functions aren't caught until runtime
- Lazarus can:
  - Analyze stack traces to locate the problem
  - Understand what the missing function should do based on context
  - Implement reasonable solutions
- This is different from syntax errors (caught before execution)

## Real-World Scenarios

This type of error commonly occurs when:
- **Refactoring**: You moved or renamed a function but missed updating all call sites
- **Incomplete implementation**: A function was planned but never written
- **Copy-paste errors**: Code references functions from a different file
- **Merge conflicts**: A function was deleted in one branch but still called in another

## Why This Matters

In production environments, runtime errors can:
- Cause data processing jobs to fail
- Break automated reports
- Interrupt scheduled tasks

Having Lazarus automatically detect and fix these issues means:
- Less manual debugging at odd hours
- Faster recovery from errors
- Reduced downtime for automated processes

## Configuration Notes

The `lazarus.yaml` specifies:
- `max_attempts: 3` - Try up to 3 times to fix
- `allowed_files: ["app.js"]` - Only modify the main application file
- Git integration enabled for automatic PR creation

## Fixed Version

A corrected version of the script is available in the `fixed/` subdirectory.

**Location:** `fixed/app.js`

**What was fixed:**
- Added the missing `getUserById(id)` function around line 24
- The function uses `Array.find()` to locate a user by ID

**To compare the broken vs fixed versions:**

```bash
# See the differences
diff app.js fixed/app.js

# Or use a side-by-side diff
diff -y app.js fixed/app.js

# Run the fixed version
node fixed/app.js
```

**Expected output from the fixed version:**
```
User Data Processor v1.0

Generating user report...

=== User Statistics ===
Total Users: 4
Active Users: 3
Inactive Users: 1

=== Featured User ===
Name: Alice
Email: alice@example.com
Status: active

Report generated successfully!
```
