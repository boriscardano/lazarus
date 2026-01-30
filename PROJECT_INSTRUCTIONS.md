
u are building Lazarus, an open-source self-healing script runner. This is a complex project requiring careful coordination.
Working Method

Create a task tracking file at TASKS.md in the project root. This file must contain all tasks, their current status (pending, in-progress, blocked, complete), their dependencies, estimated complexity (small, medium, large), and which subagent is assigned if any. Update this file continuously as you make progress.
Use subagents for tasks that can be parallelized. Before starting work, analyze the task dependency graph and identify which tasks have no blockers and can be worked on simultaneously. Spawn subagents for independent workstreams.
Create a decisions log at docs/DECISIONS.md where you document any significant architectural or implementation decisions, including the alternatives you considered and why you chose the approach you did. This is important for an open-source project so contributors understand the reasoning.
Test as you build — after completing each major component, verify it works before moving on. Do not leave a trail of broken code.
Commit frequently with clear, conventional commit messages (feat:, fix:, docs:, chore:, etc.)


Task Breakdown
Phase 1: Foundation
Task 1.1: Project Scaffolding
Dependencies: None
Complexity: Small
Parallelizable: No (must be done first)
Create the repository structure. The project root should contain:

README.md with a compelling introduction, quick start guide, feature list, and badges for license and stars
LICENSE file using MIT license
CONTRIBUTING.md with guidelines for contributors including code style, PR process, and how to run tests
CODE_OF_CONDUCT.md using the Contributor Covenant
CHANGELOG.md following Keep a Changelog format
.gitignore configured for macOS, Linux, Python, Node.js, and common editor files

Create the following directory structure:

src/ — core source code for the healing system
runner-setup/ — scripts and documentation for setting up the GitHub Actions self-hosted runner
workflows/ — GitHub Actions workflow templates that users copy to their repos
config/ — configuration file templates and schema definitions
examples/ — example scripts demonstrating different failure scenarios and how Lazarus heals them
docs/ — detailed documentation beyond the README
scripts/ — utility scripts for installation, setup, and maintenance of Lazarus itself
tests/ — test suite for the project


Task 1.2: Configuration System Design
Dependencies: Task 1.1
Complexity: Medium
Parallelizable: Yes (can run in parallel with Task 1.3)
Assign to: Subagent A
Design and implement the configuration system. Lazarus needs a configuration file that users place in their repository to control its behavior.
The configuration file should be called lazarus.yaml and support the following:
Global settings:

Maximum healing attempts before giving up (default: 3)
Maximum time allowed for each healing attempt in minutes (default: 30)
Maximum total time for all healing attempts combined in minutes (default: 90)
Branch naming pattern for fix branches (default: "lazarus/fix-{script}-{timestamp}")
Whether to auto-create PRs or just push branches (default: create PRs)
Notification settings (Slack webhook URL, email, Discord webhook, or none)
Claude Code settings: model preference if configurable, allowed tools list, disallowed tools list, max turns per healing session

Per-script settings (array of script configurations):

Path to the script
Human-readable description of what the script does (this helps Claude Code understand context)
List of files that Claude Code is allowed to modify when healing this script
List of files that Claude Code must never modify
Environment variables required by the script (names only, not values)
Dependencies or setup commands to run before the script
Custom prompt additions to give Claude Code more context about this specific script
Whether this script is idempotent (safe to re-run) or has side effects that need consideration
Custom success criteria if exit code zero is not sufficient

Create a JSON schema for validation of the configuration file. Create a configuration loader that reads the YAML, validates it against the schema, and provides sensible defaults for any missing values. The loader should provide clear error messages if the configuration is invalid, pointing to the exact line and problem.
Create template configuration files showing minimal setup and full-featured setup with comments explaining each option.

Task 1.3: Documentation Framework
Dependencies: Task 1.1
Complexity: Small
Parallelizable: Yes (can run in parallel with Task 1.2)
Assign to: Subagent B
Set up the documentation structure in the docs/ directory:

getting-started.md — step-by-step guide for first-time users, from zero to running their first self-healing script
configuration.md — complete reference for all configuration options
architecture.md — explanation of how Lazarus works internally, with diagrams described in text or Mermaid format
self-hosted-runner.md — detailed guide on setting up GitHub Actions self-hosted runner on Mac Mini and Linux
troubleshooting.md — common problems and solutions
security.md — security considerations, best practices for secrets, and what Lazarus does and does not have access to
examples.md — walkthrough of the example scripts and how to use them for testing
faq.md — frequently asked questions
DECISIONS.md — architectural decision records (start this file, it will be updated throughout development)

For now, create these files with outline structure and placeholder content indicating what will go in each section. The actual content will be filled in as features are implemented.

Phase 2: Core Healing System
Task 2.1: Error Capture and Context Building
Dependencies: Task 1.2
Complexity: Large
Parallelizable: No
Build the error capture system. When a script fails, Lazarus needs to gather comprehensive context to give Claude Code the best chance of fixing the issue.
The error capture system should collect:
Direct error information:

The full stdout and stderr output from the failed script
The exit code
The exact command that was run
The working directory
Environment variables (filtered to remove secrets — create a configurable list of patterns to redact like API_KEY, TOKEN, SECRET, PASSWORD, etc.)

Script context:

The full content of the script that failed
The description from lazarus.yaml
The list of allowed and forbidden files

Repository context:

Recent git history (last 10 commits) to understand what changed recently
Git diff of any uncommitted changes
List of files in the repository with their sizes (to help Claude Code understand the project structure)
Content of key files like package.json, requirements.txt, pyproject.toml, Cargo.toml if they exist (to understand dependencies)
Content of any README in the script's directory

Runtime context:

System information (OS version, available disk space, memory)
Timestamp of the failure
Previous healing attempts for this script if any (so Claude Code knows what has already been tried)

Create a context builder that assembles all this information into a structured format. The output should be a single text document optimized for Claude Code to understand, with clear section headers and organization. Consider token limits — if the context is very large, implement intelligent truncation that preserves the most important information (error messages are most important, then the script itself, then related files, then general context).
Create a secrets redaction system that scans all captured content and replaces anything matching secret patterns with "[REDACTED]". This must be thorough — scan environment variables, file contents, and command output. Err on the side of over-redacting.

Task 2.2: Claude Code Integration
Dependencies: Task 2.1
Complexity: Large
Parallelizable: No
Build the integration with Claude Code CLI. This is the core of the healing system.
Create a healing orchestrator that:

Takes the context built in Task 2.1 and constructs a prompt for Claude Code
The prompt should follow this structure:

System context explaining that this is Lazarus, a self-healing system, and Claude Code's job is to fix the failing script
Clear statement of the goal: fix the script so it runs successfully
The error information and context from Task 2.1
Explicit instructions about which files can be modified and which cannot
Instructions to make minimal, targeted changes — do not refactor unrelated code
Instructions to explain the reasoning before making changes
Instructions about what to do if the fix requires external action (like updating an API key) — in this case, Claude Code should document what the user needs to do rather than attempting an impossible fix


Invoke Claude Code using the CLI with appropriate flags:

Use print mode (the -p flag) to pass the prompt
Configure allowed tools based on lazarus.yaml settings
Set appropriate turn limits
Capture all output from Claude Code for logging


After Claude Code completes, determine what happened:

Did Claude Code make changes? (check git status)
Did Claude Code report that it could not fix the issue?
Did Claude Code hit the turn limit?
Did Claude Code encounter an error?


If changes were made, commit them with a descriptive message that includes:

What was fixed
Summary of Claude Code's reasoning
Reference to the original error



Create robust error handling for the Claude Code invocation:

Handle the case where Claude Code is not installed
Handle authentication failures (missing or invalid API key)
Handle rate limiting
Handle network failures
Handle the case where Claude Code crashes or times out

Create a logging system that records the full interaction with Claude Code for debugging and transparency. Users should be able to see exactly what Lazarus asked Claude Code and what Claude Code responded.

Task 2.3: Script Re-execution and Verification
Dependencies: Task 2.2
Complexity: Medium
Parallelizable: No
Build the script re-execution system that verifies whether Claude Code's fix actually worked.
Create a script runner that:

Executes the script in the same way it was originally run (same working directory, same environment setup)
Captures output and exit code
Applies the success criteria from lazarus.yaml:

Default is exit code zero
Support custom success criteria like checking for specific output strings or checking that certain files were created


Returns a clear result: success, failure with new error, or same error as before

Create comparison logic that can determine if a failure after healing is:

The same error as before (Claude Code's fix did not address the issue)
A different error (Claude Code may have introduced a new problem or partially fixed the issue)
A success (the script now works)

This distinction is important for the retry loop — if it is the same error, Claude Code should be told that its fix did not work and needs to try a different approach. If it is a different error, Claude Code should be given the new error information.

Task 2.4: Healing Loop Orchestration
Dependencies: Task 2.3
Complexity: Medium
Parallelizable: No
Build the main healing loop that coordinates the entire process.
The healing loop should:

Load configuration from lazarus.yaml
Receive a script path and initial error information
Create a feature branch with the naming pattern from configuration
Enter the healing loop:

Build context (Task 2.1)
Invoke Claude Code (Task 2.2)
If Claude Code made changes, commit them
Re-run the script (Task 2.3)
If success, exit loop with success status
If failure and attempts remain, add information about what was tried to the context and continue loop
If failure and no attempts remain, exit loop with failure status


Track timing to enforce the per-attempt and total time limits
After loop exits:

If success: push branch, create PR (or just push branch if configured)
If failure: push branch with partial progress, notify user of failure


Return to original branch (usually main) and clean up any temporary files

Create detailed logging throughout the loop so users can follow what happened. Each healing attempt should be clearly numbered and its outcome recorded.
Handle edge cases:

What if the repository has uncommitted changes when healing starts? (Stash them, restore after)
What if there are merge conflicts when creating the branch? (Report to user)
What if pushing fails? (Retry with backoff, then report to user)
What if PR creation fails? (Still preserve the branch, report to user)


Phase 3: GitHub Integration
Task 3.1: Pull Request Creation
Dependencies: Task 2.4
Complexity: Medium
Parallelizable: Yes (can run in parallel with Task 3.2)
Assign to: Subagent C
Build the pull request creation system using the GitHub CLI (gh).
The PR creation should:

Check that gh is installed and authenticated
Push the feature branch to origin
Create a PR with a well-structured body that includes:

Title: "fix: Lazarus auto-heal for {script name}"
Summary of what script failed and why
The original error message (truncated if very long)
List of changes made by Claude Code with brief explanations
Number of healing attempts it took
Clear note that this is an automated fix and should be reviewed by a human
Link to the full healing log if available
Instructions for how to test the fix locally
Labels: "lazarus", "auto-fix", and any custom labels from configuration


Handle existing PRs — if there is already an open Lazarus PR for this script, either update it or create a new one based on configuration
Support draft PRs as a configuration option for users who want to review before the PR is visible to the team

Create templates for the PR body that can be customized in configuration.

Task 3.2: GitHub Actions Workflow Templates
Dependencies: Task 1.2
Complexity: Medium
Parallelizable: Yes (can run in parallel with Task 3.1)
Assign to: Subagent D
Create GitHub Actions workflow templates that users copy to their repositories.
Create the following workflow templates:
lazarus-scheduled.yaml:

Triggered by cron schedule (user configures the schedule)
Also supports manual trigger via workflow_dispatch for testing
Runs on self-hosted runner
Checks out the repository
Runs the scheduled script
If the script fails, invokes the Lazarus healing system
Reports results via configured notification channels

lazarus-on-failure.yaml:

Can be called by other workflows when a step fails
Reusable workflow that takes the failed script path and error log as inputs
Invokes the Lazarus healing system
Useful for adding self-healing to existing CI workflows

lazarus-manual.yaml:

Triggered manually via workflow_dispatch
Takes script path as input
Runs the script and heals if it fails
Useful for testing Lazarus on a specific script

Each workflow should:

Have detailed comments explaining what each step does
Include proper error handling so the workflow itself does not fail cryptically
Support passing secrets via GitHub secrets (ANTHROPIC_API_KEY, SLACK_WEBHOOK, etc.)
Output clear status information

Create a setup script that users can run to automatically copy these workflows to their repository's .github/workflows directory with some basic customization prompts.

Task 3.3: Self-Hosted Runner Setup Guide and Scripts
Dependencies: Task 1.3
Complexity: Medium
Parallelizable: Yes (can run in parallel with Task 3.1 and 3.2)
Assign to: Subagent E
Create comprehensive documentation and helper scripts for setting up a GitHub Actions self-hosted runner on Mac Mini.
Documentation should cover:
For Mac Mini:

System requirements (macOS version, disk space, memory recommendations)
Creating a dedicated user account for the runner (recommended for security)
Downloading and configuring the GitHub Actions runner
Installing the runner as a launchd service so it starts automatically and survives reboots
Configuring the runner with appropriate labels (lazarus, self-hosted, macOS, etc.)
Security hardening recommendations (firewall, limited user permissions)
How to update the runner
How to monitor runner health

For Linux (secondary platform):

Similar guide adapted for Linux
systemd service configuration instead of launchd

Helper scripts to create:

install-runner.sh — interactive script that walks users through runner installation
configure-launchd.sh — sets up the launchd service on macOS with recommended settings
configure-systemd.sh — sets up the systemd service on Linux
check-runner-health.sh — verifies the runner is working correctly
update-runner.sh — safely updates the runner to the latest version

Each script should:

Check for prerequisites before proceeding
Provide clear progress messages
Handle errors gracefully with helpful messages
Be idempotent where possible (safe to run multiple times)
Never require root unless absolutely necessary, and explain why if it does


Phase 4: Notifications and Observability
Task 4.1: Notification System
Dependencies: Task 2.4
Complexity: Medium
Parallelizable: Yes
Assign to: Subagent F
Build a notification system that alerts users about healing results.
Support the following notification channels:
Slack:

Post to a configured webhook URL
Rich message format with script name, status, error summary, link to PR if created
Different formatting for success (green) vs failure (red)
Include action buttons if Slack webhook supports them (link to PR, link to logs)

Discord:

Similar to Slack but adapted for Discord webhook format
Use embeds for rich formatting

Email:

Send via configured SMTP server or a simple service like SendGrid
HTML and plain text versions
Clear subject line indicating success or failure

GitHub Issues:

Create an issue when healing fails after all retries
Issue should contain all the information someone would need to investigate
Apply configured labels
Assign to configured users if desired

Custom webhook:

Support arbitrary webhook URLs for users who want to integrate with other systems
POST a JSON payload with all relevant information
Document the payload schema

Create a notification dispatcher that:

Reads notification configuration from lazarus.yaml
Supports sending to multiple channels simultaneously
Handles failures in notification delivery gracefully (log but do not crash)
Respects rate limits for each service


Task 4.2: Logging and History
Dependencies: Task 2.4
Complexity: Medium
Parallelizable: Yes
Assign to: Subagent G
Build a logging system that maintains history of all healing attempts.
Create a local log storage system that:

Stores detailed logs for each healing session in a structured format (JSON)
Includes: timestamp, script path, original error, all healing attempts with their prompts and responses, final outcome, time taken, files modified, PR link if created
Organizes logs by date and script name for easy navigation
Implements log rotation to prevent unbounded growth (configurable retention period)

Create a log viewer command that:

Lists recent healing sessions with summary information
Shows detailed information for a specific session
Filters by script, date range, or outcome (success/failure)
Exports logs in formats suitable for analysis (JSON, CSV)

Create GitHub Actions artifacts integration:

Upload healing logs as workflow artifacts so they are accessible from the GitHub UI
Set appropriate retention period

Document how users can integrate Lazarus logs with external observability tools if desired (the JSON format should make this straightforward).

Phase 5: Examples and Testing
Task 5.1: Example Scripts
Dependencies: Task 2.4
Complexity: Medium
Parallelizable: Yes
Assign to: Subagent H
Create a set of example scripts that demonstrate Lazarus capabilities and can be used for testing.
Example 1: Python script with fixable syntax error

A Python script that does something simple (fetches data from a public API, processes it, writes a summary)
Intentionally contains a syntax error that Claude Code should easily fix
Include a working version and a broken version so users can test the healing

Example 2: Shell script with incorrect command

A bash script that performs some file operations
Contains a typo in a command name or incorrect flag
Demonstrates healing of shell scripts

Example 3: Node.js script with runtime error

A Node.js script that processes JSON data
Has a runtime error (accessing property of undefined, off-by-one error, etc.)
Includes package.json with dependencies

Example 4: Script that fails due to external changes

Simulates a script that fails because an API changed its response format
Demonstrates how Claude Code can adapt to external changes

Example 5: Script with multiple related files

A more complex scenario where the fix requires modifying a helper module, not just the main script
Demonstrates that Claude Code can work across files within the allowed list

Example 6: Script that cannot be auto-fixed

A script that fails for a reason Claude Code cannot fix (missing API key, external service down)
Demonstrates that Lazarus correctly identifies unfixable issues and reports them to the user

For each example, create:

The script itself with the intentional bug
A fixed version in a separate directory for reference
A README explaining what the example demonstrates
The appropriate lazarus.yaml configuration
Instructions for how to run the example


Task 5.2: Test Suite
Dependencies: Task 5.1
Complexity: Large
Parallelizable: Partially (can start after some core components are done)
Create a comprehensive test suite for Lazarus.
Unit tests for:

Configuration loading and validation
Secrets redaction (verify secrets are properly removed from various contexts)
Context building (verify all expected information is included)
Error comparison logic (same error vs different error vs success)
Notification message formatting
Log parsing and storage

Integration tests for:

Full healing loop with mock Claude Code responses
PR creation with mock GitHub CLI
Each notification channel with mock endpoints
Runner setup scripts in a clean environment

End-to-end tests:

Use the example scripts to run actual healing sessions
These tests require Claude Code to be available and will use real API calls
Mark these tests as optional/slow so they do not run on every commit
Create a GitHub Actions workflow that runs end-to-end tests on a schedule (weekly) or manually

Use a testing framework appropriate for the implementation language. Structure tests clearly so contributors can easily add tests for new features.
Create a TESTING.md document explaining:

How to run the test suite
How to run specific categories of tests
How to write new tests
What the mock system provides and how to use it


Phase 6: Polish and Release
Task 6.1: README and Documentation Completion
Dependencies: All previous tasks
Complexity: Medium
Parallelizable: No
Complete all documentation with actual content now that the implementation is done.
The README should include:

Eye-catching header with project name and one-line description
Animated GIF or screenshot showing Lazarus in action (create a simple demo recording)
Badges for license, latest release, build status
Clear problem statement: why Lazarus exists
Quick start guide that gets users from zero to first successful healing in under 10 minutes
Feature highlights with brief explanations
Link to full documentation
Contributing section with link to CONTRIBUTING.md
License section
Acknowledgments (Claude Code, GitHub Actions, any libraries used)

Review and complete all documentation files created in Task 1.3. Ensure accuracy against the actual implementation. Add real examples and command output where helpful.
Create a SECURITY.md file explaining:

How to report security vulnerabilities
Security considerations when running Lazarus
What Lazarus does and does not have access to
Recommendations for secure usage


Task 6.2: Installation and Distribution
Dependencies: Task 6.1
Complexity: Small
Parallelizable: No
Create installation methods for users.
Simple installation:

Clone the repository
Run an install script that copies files to appropriate locations
The install script should check prerequisites (git, gh CLI, claude CLI)

Homebrew (stretch goal):

Create a Homebrew formula so users can install with brew install lazarus
Document how to publish to Homebrew

Create an uninstall script that cleanly removes Lazarus.
Create an update script that pulls the latest version and reinstalls.
Document version compatibility requirements (minimum versions of git, gh CLI, claude CLI, macOS, bash, etc.)

Task 6.3: First Release
Dependencies: Task 6.2
Complexity: Small
Parallelizable: No
Prepare for the first public release.

Review all code for any hardcoded values that should be configurable
Review all documentation for accuracy and clarity
Ensure all example scripts work
Run the full test suite
Create a GitHub release with version 0.1.0
Write release notes explaining what Lazarus does and how to get started
Create a simple landing page or update the repository description and topics for discoverability


Final Notes for Claude Code
As you implement this project, keep the following in mind:

Prioritize working software over perfection. Get a basic end-to-end flow working first, then improve it.
The healing prompt is critical. Spend extra effort crafting the prompt that Lazarus sends to Claude Code. The quality of healing depends heavily on giving Claude Code the right context and instructions.
Security cannot be an afterthought. The secrets redaction system is critical. Test it thoroughly with various secret patterns. A user's API keys should never end up in a GitHub PR or log file.
User experience matters. Clear error messages, helpful progress output, and good defaults make the difference between a tool people use and one they abandon.
Open source ethos. Write code that others can read and contribute to. Add comments explaining non-obvious decisions. Keep the architecture simple enough that someone can understand it by reading the code.
Test the examples yourself. Before marking tasks complete, actually run through the examples as a user would. Does the experience make sense? Is anything confusing?

When you complete all tasks, create a final summary in TASKS.md listing what was accomplished, any known limitations or future improvement ideas, and confirmation that the project is ready for release.

