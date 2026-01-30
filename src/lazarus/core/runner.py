"""Script runner with verification support.

This module provides the ScriptRunner class for executing scripts, capturing
their output, and verifying fixes by re-running scripts and comparing results.
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from lazarus.config.schema import LazarusConfig, ScriptConfig
from lazarus.core.context import ExecutionResult
from lazarus.core.verification import (
    ErrorComparison,
    VerificationResult,
    check_custom_criteria,
    compare_errors,
)


class ScriptRunner:
    """Script runner with support for various script types and verification.

    This class handles:
    - Detecting script types (Python, Bash, Node.js, etc.)
    - Running scripts with timeout and output capture
    - Verifying fixes by comparing execution results
    - Supporting custom success criteria

    Attributes:
        config: Lazarus configuration with global settings
    """

    def __init__(self, config: LazarusConfig) -> None:
        """Initialize the script runner.

        Args:
            config: Lazarus configuration object
        """
        self.config = config

    def run_script(
        self,
        script_path: Path,
        working_dir: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> ExecutionResult:
        """Run a script and capture its execution result.

        This method automatically detects the script type and runs it with the
        appropriate interpreter, capturing stdout, stderr, exit code, and duration.

        Args:
            script_path: Path to the script file to execute
            working_dir: Working directory for script execution (defaults to script's directory)
            env: Additional environment variables to set (merged with current environment)
            timeout: Maximum execution time in seconds (default: 300)

        Returns:
            ExecutionResult containing execution details

        Raises:
            FileNotFoundError: If script_path does not exist
            PermissionError: If script is not readable or executable
            ValueError: If script type cannot be determined

        Example:
            >>> runner = ScriptRunner(config)
            >>> result = runner.run_script(Path("scripts/test.py"), timeout=60)
            >>> print(f"Exit code: {result.exit_code}")
            >>> print(f"Duration: {result.duration}s")
        """
        # Validate script exists
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        if not script_path.is_file():
            raise ValueError(f"Path is not a file: {script_path}")

        # Determine working directory
        if working_dir is None:
            working_dir = script_path.parent.resolve()

        # Build environment
        script_env = os.environ.copy()
        if env:
            script_env.update(env)

        # Get interpreter command for the script
        interpreter_cmd = self.get_interpreter(script_path)

        # Prepare full command
        cmd = interpreter_cmd + [str(script_path.resolve())]

        # Execute the script
        start_time = time.time()
        timestamp = datetime.now(UTC)

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                env=script_env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                timestamp=timestamp,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""
            stderr += f"\n[TIMEOUT] Script execution exceeded {timeout} seconds"

            return ExecutionResult(
                exit_code=-1,  # Special code for timeout
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                timestamp=timestamp,
            )

        except (OSError, subprocess.SubprocessError) as e:
            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=-2,  # Special code for execution error
                stdout="",
                stderr=f"[EXECUTION ERROR] {type(e).__name__}: {e}",
                duration=duration,
                timestamp=timestamp,
            )

    def verify_fix(
        self,
        script_path: Path,
        previous_result: ExecutionResult,
        config: ScriptConfig | None = None,
    ) -> VerificationResult:
        """Verify that a script fix was successful by re-running the script.

        This method re-executes the script and compares the new result with the
        previous failed execution to determine if the fix was successful.

        Args:
            script_path: Path to the (potentially fixed) script
            previous_result: The previous failed execution result
            config: Optional script-specific configuration for custom criteria

        Returns:
            VerificationResult with status and comparison details

        Example:
            >>> runner = ScriptRunner(config)
            >>> previous = ExecutionResult(exit_code=1, stdout="", stderr="Error!", duration=0.1)
            >>> verification = runner.verify_fix(Path("script.py"), previous)
            >>> if verification.status == "success":
            ...     print("Fix verified!")
        """
        # Determine timeout and working directory from config
        timeout = config.timeout if config else 300
        working_dir = config.working_dir if config else None

        # Prepare environment with required variables
        env: dict[str, str] | None = None
        if config and config.environment:
            env = {}
            for var_name in config.environment:
                if var_name in os.environ:
                    env[var_name] = os.environ[var_name]

        # Re-run the script
        current_result = self.run_script(
            script_path=script_path,
            working_dir=working_dir,
            env=env,
            timeout=timeout,
        )

        # Compare with previous result
        comparison = compare_errors(previous_result, current_result)

        # Check custom success criteria if provided
        custom_criteria_passed: bool | None = None
        if config and config.success_criteria:
            custom_criteria_passed = check_custom_criteria(
                current_result, config.success_criteria
            )

        # Determine verification status
        status = self._determine_verification_status(
            current_result, comparison, custom_criteria_passed
        )

        return VerificationResult(
            status=status,
            execution_result=current_result,
            comparison=comparison,
            custom_criteria_passed=custom_criteria_passed,
        )

    def detect_script_type(self, script_path: Path) -> str:
        """Detect the type of script based on extension and shebang.

        Supported types:
        - python: .py files or #!/usr/bin/env python
        - bash: .sh files or #!/bin/bash, #!/bin/sh
        - node: .js, .mjs files or #!/usr/bin/env node
        - ruby: .rb files or #!/usr/bin/env ruby
        - perl: .pl files or #!/usr/bin/env perl
        - executable: Files with executable permission and no recognized type

        Args:
            script_path: Path to the script file

        Returns:
            String identifier for the script type

        Raises:
            ValueError: If script type cannot be determined

        Example:
            >>> runner = ScriptRunner(config)
            >>> runner.detect_script_type(Path("test.py"))
            'python'
            >>> runner.detect_script_type(Path("deploy.sh"))
            'bash'
        """
        # Check file extension first (fast path)
        extension = script_path.suffix.lower()
        extension_map = {
            ".py": "python",
            ".sh": "bash",
            ".bash": "bash",
            ".js": "node",
            ".mjs": "node",
            ".ts": "node",  # TypeScript (requires ts-node or compilation)
            ".rb": "ruby",
            ".pl": "perl",
            ".php": "php",
        }

        if extension in extension_map:
            return extension_map[extension]

        # Check shebang line
        try:
            with open(script_path, encoding="utf-8") as f:
                first_line = f.readline().strip()

            if first_line.startswith("#!"):
                shebang = first_line[2:].strip()

                # Extract the interpreter from the shebang
                if "python" in shebang:
                    return "python"
                elif "bash" in shebang or shebang.endswith("/sh"):
                    return "bash"
                elif "node" in shebang:
                    return "node"
                elif "ruby" in shebang:
                    return "ruby"
                elif "perl" in shebang:
                    return "perl"
                elif "php" in shebang:
                    return "php"

        except (OSError, UnicodeDecodeError):
            # If we can't read the file, continue to check executability
            pass

        # Check if file is executable
        if os.access(script_path, os.X_OK):
            return "executable"

        raise ValueError(
            f"Cannot determine script type for {script_path}. "
            "File has no recognized extension, shebang, or executable permission."
        )

    def get_interpreter(self, script_path: Path) -> list[str]:
        """Get the command to run a script based on its type.

        Args:
            script_path: Path to the script file

        Returns:
            List of command parts to execute the script (e.g., ["python3"] or [])

        Raises:
            ValueError: If script type cannot be determined

        Example:
            >>> runner = ScriptRunner(config)
            >>> runner.get_interpreter(Path("test.py"))
            ['python3']
            >>> runner.get_interpreter(Path("deploy.sh"))
            ['bash']
        """
        script_type = self.detect_script_type(script_path)

        # Map script types to interpreter commands
        interpreter_map = {
            "python": ["python3"],
            "bash": ["bash"],
            "node": ["node"],
            "ruby": ["ruby"],
            "perl": ["perl"],
            "php": ["php"],
            "executable": [],  # No interpreter needed for executable files
        }

        if script_type not in interpreter_map:
            raise ValueError(f"No interpreter configured for script type: {script_type}")

        return interpreter_map[script_type]

    def _determine_verification_status(
        self,
        current_result: ExecutionResult,
        comparison: ErrorComparison,
        custom_criteria_passed: bool | None,
    ) -> str:
        """Determine the verification status based on execution result and comparison.

        Args:
            current_result: The current execution result
            comparison: Comparison with previous execution
            custom_criteria_passed: Whether custom criteria were met (if applicable)

        Returns:
            Status string: "success", "same_error", "different_error", or "timeout"
        """
        # Check for timeout (special exit code -1)
        if current_result.exit_code == -1:
            return "timeout"

        # If custom criteria are defined, they take precedence
        if custom_criteria_passed is not None:
            if custom_criteria_passed:
                return "success"
            else:
                # Custom criteria failed - determine if error changed
                return "same_error" if comparison.is_same_error else "different_error"

        # No custom criteria - use standard success check
        if current_result.success:
            return "success"

        # Script still failed - check if it's the same error or different
        if comparison.is_same_error:
            return "same_error"
        else:
            return "different_error"
