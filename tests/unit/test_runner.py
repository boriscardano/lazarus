"""Unit tests for ScriptRunner class."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lazarus.config.schema import LazarusConfig, ScriptConfig
from lazarus.core.context import ExecutionResult
from lazarus.core.runner import ScriptRunner
from lazarus.core.verification import ErrorComparison, VerificationResult


class TestScriptRunnerInit:
    """Tests for ScriptRunner initialization."""

    def test_init_with_config(self):
        """Test ScriptRunner initialization with config."""
        config = LazarusConfig()
        runner = ScriptRunner(config)
        assert runner.config == config

    def test_init_with_custom_config(self):
        """Test ScriptRunner initialization with custom config."""
        config = LazarusConfig()
        config.healing.max_attempts = 5
        runner = ScriptRunner(config)
        assert runner.config.healing.max_attempts == 5


class TestDetectScriptType:
    """Tests for detect_script_type method."""

    def test_detect_python_by_extension(self, tmp_path):
        """Test detecting Python script by .py extension."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "python"

    def test_detect_bash_by_extension(self, tmp_path):
        """Test detecting Bash script by .sh extension."""
        script = tmp_path / "test.sh"
        script.write_text("echo 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "bash"

    def test_detect_bash_by_bash_extension(self, tmp_path):
        """Test detecting Bash script by .bash extension."""
        script = tmp_path / "test.bash"
        script.write_text("echo 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "bash"

    def test_detect_node_by_js_extension(self, tmp_path):
        """Test detecting Node.js script by .js extension."""
        script = tmp_path / "test.js"
        script.write_text("console.log('hello');")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "node"

    def test_detect_node_by_mjs_extension(self, tmp_path):
        """Test detecting Node.js script by .mjs extension."""
        script = tmp_path / "test.mjs"
        script.write_text("console.log('hello');")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "node"

    def test_detect_ruby_by_extension(self, tmp_path):
        """Test detecting Ruby script by .rb extension."""
        script = tmp_path / "test.rb"
        script.write_text("puts 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "ruby"

    def test_detect_perl_by_extension(self, tmp_path):
        """Test detecting Perl script by .pl extension."""
        script = tmp_path / "test.pl"
        script.write_text("print 'hello';")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "perl"

    def test_detect_php_by_extension(self, tmp_path):
        """Test detecting PHP script by .php extension."""
        script = tmp_path / "test.php"
        script.write_text("<?php echo 'hello'; ?>")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "php"

    def test_detect_python_by_shebang(self, tmp_path):
        """Test detecting Python script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/usr/bin/env python\nprint('hello')")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "python"

    def test_detect_bash_by_shebang(self, tmp_path):
        """Test detecting Bash script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/bin/bash\necho 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "bash"

    def test_detect_sh_by_shebang(self, tmp_path):
        """Test detecting shell script by /bin/sh shebang."""
        script = tmp_path / "test"
        script.write_text("#!/bin/sh\necho 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "bash"

    def test_detect_node_by_shebang(self, tmp_path):
        """Test detecting Node.js script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/usr/bin/env node\nconsole.log('hello');")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "node"

    def test_detect_ruby_by_shebang(self, tmp_path):
        """Test detecting Ruby script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/usr/bin/env ruby\nputs 'hello'")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "ruby"

    def test_detect_perl_by_shebang(self, tmp_path):
        """Test detecting Perl script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/usr/bin/env perl\nprint 'hello';")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "perl"

    def test_detect_php_by_shebang(self, tmp_path):
        """Test detecting PHP script by shebang."""
        script = tmp_path / "test"
        script.write_text("#!/usr/bin/env php\n<?php echo 'hello'; ?>")

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "php"

    def test_detect_executable_without_extension(self, tmp_path):
        """Test detecting executable script without extension."""
        script = tmp_path / "test"
        script.write_text("some content")
        script.chmod(0o755)  # Make executable

        runner = ScriptRunner(LazarusConfig())
        script_type = runner.detect_script_type(script)
        assert script_type == "executable"

    def test_detect_script_type_unrecognized(self, tmp_path):
        """Test detecting script type for unrecognized file."""
        script = tmp_path / "test.unknown"
        script.write_text("some content")

        runner = ScriptRunner(LazarusConfig())
        with pytest.raises(ValueError, match="Cannot determine script type"):
            runner.detect_script_type(script)

    def test_detect_script_type_unicode_decode_error(self, tmp_path):
        """Test detecting script type when file has encoding issues."""
        script = tmp_path / "test"
        # Write binary data that's not valid UTF-8
        script.write_bytes(b"\x80\x81\x82")

        runner = ScriptRunner(LazarusConfig())
        # Should fall through to checking executable permission
        with pytest.raises(ValueError, match="Cannot determine script type"):
            runner.detect_script_type(script)


class TestGetInterpreter:
    """Tests for get_interpreter method."""

    def test_get_interpreter_python(self, tmp_path):
        """Test getting interpreter for Python script."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["python3"]

    def test_get_interpreter_bash(self, tmp_path):
        """Test getting interpreter for Bash script."""
        script = tmp_path / "test.sh"
        script.write_text("echo 'hello'")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["bash"]

    def test_get_interpreter_node(self, tmp_path):
        """Test getting interpreter for Node.js script."""
        script = tmp_path / "test.js"
        script.write_text("console.log('hello');")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["node"]

    def test_get_interpreter_ruby(self, tmp_path):
        """Test getting interpreter for Ruby script."""
        script = tmp_path / "test.rb"
        script.write_text("puts 'hello'")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["ruby"]

    def test_get_interpreter_perl(self, tmp_path):
        """Test getting interpreter for Perl script."""
        script = tmp_path / "test.pl"
        script.write_text("print 'hello';")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["perl"]

    def test_get_interpreter_php(self, tmp_path):
        """Test getting interpreter for PHP script."""
        script = tmp_path / "test.php"
        script.write_text("<?php echo 'hello'; ?>")

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == ["php"]

    def test_get_interpreter_executable(self, tmp_path):
        """Test getting interpreter for executable file."""
        script = tmp_path / "test"
        script.write_text("#!/bin/custom\necho 'hello'")
        script.chmod(0o755)

        runner = ScriptRunner(LazarusConfig())
        interpreter = runner.get_interpreter(script)
        assert interpreter == []

    @patch("lazarus.core.runner.ScriptRunner.detect_script_type")
    def test_get_interpreter_unknown_script_type(self, mock_detect, tmp_path):
        """Test getting interpreter for unknown script type."""
        script = tmp_path / "test.unknown"
        script.write_text("some content")

        # Mock detect_script_type to return an unknown type
        mock_detect.return_value = "unknown_type"

        runner = ScriptRunner(LazarusConfig())
        with pytest.raises(ValueError, match="No interpreter configured for script type"):
            runner.get_interpreter(script)


class TestRunScript:
    """Tests for run_script method."""

    @patch("subprocess.run")
    def test_run_script_success(self, mock_run, tmp_path):
        """Test running a successful script."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "hello\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script)

        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.success is True
        assert result.duration > 0
        assert isinstance(result.timestamp, datetime)

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["python3", str(script.resolve())]
        assert call_args[1]["cwd"] == script.parent.resolve()
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["timeout"] == 300

    @patch("subprocess.run")
    def test_run_script_failure(self, mock_run, tmp_path):
        """Test running a failing script."""
        script = tmp_path / "test.py"
        script.write_text("raise ValueError('error')")

        # Mock failed execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ValueError: error"
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script)

        assert result.exit_code == 1
        assert result.stderr == "ValueError: error"
        assert result.success is False

    @patch("subprocess.run")
    def test_run_script_with_custom_timeout(self, mock_run, tmp_path):
        """Test running script with custom timeout."""
        script = tmp_path / "test.sh"
        script.write_text("echo 'hello'")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "hello\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script, timeout=60)

        assert result.exit_code == 0
        call_args = mock_run.call_args
        assert call_args[1]["timeout"] == 60

    @patch("subprocess.run")
    def test_run_script_with_working_dir(self, mock_run, tmp_path):
        """Test running script with custom working directory."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")
        working_dir = tmp_path / "workdir"
        working_dir.mkdir()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "hello\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script, working_dir=working_dir)

        assert result.exit_code == 0
        call_args = mock_run.call_args
        assert call_args[1]["cwd"] == working_dir

    @patch("subprocess.run")
    def test_run_script_with_env_vars(self, mock_run, tmp_path):
        """Test running script with environment variables."""
        script = tmp_path / "test.py"
        script.write_text("import os; print(os.environ.get('TEST_VAR'))")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_value\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())
        custom_env = {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
        result = runner.run_script(script, env=custom_env)

        assert result.exit_code == 0
        call_args = mock_run.call_args
        # Env should be merged with os.environ
        assert "TEST_VAR" in call_args[1]["env"]
        assert call_args[1]["env"]["TEST_VAR"] == "test_value"
        assert "ANOTHER_VAR" in call_args[1]["env"]
        # Should also include system environment
        assert "PATH" in call_args[1]["env"]

    @patch("subprocess.run")
    def test_run_script_timeout_expired(self, mock_run, tmp_path):
        """Test handling timeout during script execution."""
        script = tmp_path / "test.py"
        script.write_text("import time; time.sleep(1000)")

        # Mock timeout
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["python3", str(script)],
            timeout=1,
            output=b"partial output",
            stderr=b"partial error"
        )
        mock_run.side_effect = timeout_exc

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script, timeout=1)

        assert result.exit_code == -1  # Special code for timeout
        assert result.stdout == "partial output"
        assert "[TIMEOUT]" in result.stderr
        assert "exceeded 1 seconds" in result.stderr
        assert result.duration > 0

    @patch("subprocess.run")
    def test_run_script_timeout_no_output(self, mock_run, tmp_path):
        """Test handling timeout with no captured output."""
        script = tmp_path / "test.py"
        script.write_text("import time; time.sleep(1000)")

        # Mock timeout with no output
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["python3", str(script)],
            timeout=1,
            output=None,
            stderr=None
        )
        mock_run.side_effect = timeout_exc

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script, timeout=1)

        assert result.exit_code == -1
        assert result.stdout == ""
        assert "[TIMEOUT]" in result.stderr

    @patch("subprocess.run")
    def test_run_script_os_error(self, mock_run, tmp_path):
        """Test handling OSError during script execution."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Mock OSError
        mock_run.side_effect = OSError("No such file or directory")

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script)

        assert result.exit_code == -2  # Special code for execution error
        assert result.stdout == ""
        assert "[EXECUTION ERROR]" in result.stderr
        assert "OSError" in result.stderr
        assert "No such file or directory" in result.stderr

    @patch("subprocess.run")
    def test_run_script_subprocess_error(self, mock_run, tmp_path):
        """Test handling SubprocessError during script execution."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Mock SubprocessError
        mock_run.side_effect = subprocess.SubprocessError("Subprocess failed")

        runner = ScriptRunner(LazarusConfig())
        result = runner.run_script(script)

        assert result.exit_code == -2
        assert "[EXECUTION ERROR]" in result.stderr
        assert "SubprocessError" in result.stderr

    def test_run_script_file_not_found(self, tmp_path):
        """Test running a script that doesn't exist."""
        script = tmp_path / "nonexistent.py"

        runner = ScriptRunner(LazarusConfig())
        with pytest.raises(FileNotFoundError, match="Script not found"):
            runner.run_script(script)

    def test_run_script_path_is_directory(self, tmp_path):
        """Test running a path that is a directory, not a file."""
        directory = tmp_path / "testdir"
        directory.mkdir()

        runner = ScriptRunner(LazarusConfig())
        with pytest.raises(ValueError, match="Path is not a file"):
            runner.run_script(directory)

    @patch("subprocess.run")
    def test_run_script_different_script_types(self, mock_run, tmp_path):
        """Test running different script types."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = ScriptRunner(LazarusConfig())

        # Test bash script
        bash_script = tmp_path / "test.sh"
        bash_script.write_text("echo 'hello'")
        result = runner.run_script(bash_script)
        assert result.exit_code == 0
        assert mock_run.call_args[0][0][0] == "bash"

        # Test node script
        node_script = tmp_path / "test.js"
        node_script.write_text("console.log('hello');")
        result = runner.run_script(node_script)
        assert result.exit_code == 0
        assert mock_run.call_args[0][0][0] == "node"


class TestVerifyFix:
    """Tests for verify_fix method."""

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    def test_verify_fix_success(self, mock_compare, mock_run_script, tmp_path):
        """Test verifying a successful fix."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Previous failed execution
        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error occurred",
            duration=0.5,
        )

        # Current successful execution
        current_result = ExecutionResult(
            exit_code=0,
            stdout="hello\n",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        # Mock comparison
        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=["Exit code changed from 1 to 0"],
        )
        mock_compare.return_value = mock_comparison

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result)

        assert verification.status == "success"
        assert verification.execution_result == current_result
        assert verification.comparison == mock_comparison
        assert verification.custom_criteria_passed is None

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    def test_verify_fix_same_error(self, mock_compare, mock_run_script, tmp_path):
        """Test verifying when same error persists."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Previous failed execution
        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ValueError: invalid input",
            duration=0.5,
        )

        # Current execution with same error
        current_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ValueError: invalid input",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        # Mock comparison showing same error
        mock_comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.95,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result)

        assert verification.status == "same_error"
        assert verification.execution_result == current_result

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    def test_verify_fix_different_error(self, mock_compare, mock_run_script, tmp_path):
        """Test verifying when different error occurs."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        # Previous failed execution
        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ValueError: invalid input",
            duration=0.5,
        )

        # Current execution with different error
        current_result = ExecutionResult(
            exit_code=2,
            stdout="",
            stderr="KeyError: missing key",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        # Mock comparison showing different error
        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.2,
            key_differences=["Exit code changed from 1 to 2"],
        )
        mock_compare.return_value = mock_comparison

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result)

        assert verification.status == "different_error"
        assert verification.execution_result == current_result

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    def test_verify_fix_timeout(self, mock_compare, mock_run_script, tmp_path):
        """Test verifying when timeout occurs."""
        script = tmp_path / "test.py"
        script.write_text("import time; time.sleep(1000)")

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        # Current execution timed out
        current_result = ExecutionResult(
            exit_code=-1,  # Timeout exit code
            stdout="",
            stderr="[TIMEOUT] Script execution exceeded 60 seconds",
            duration=60.0,
        )
        mock_run_script.return_value = current_result

        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.0,
            key_differences=["Exit code changed from 1 to -1"],
        )
        mock_compare.return_value = mock_comparison

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result)

        assert verification.status == "timeout"

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    @patch("lazarus.core.runner.check_custom_criteria")
    def test_verify_fix_with_custom_criteria_passed(
        self, mock_check_criteria, mock_compare, mock_run_script, tmp_path
    ):
        """Test verifying with custom criteria that pass."""
        script = tmp_path / "test.py"
        script.write_text("print('Success: 100 items')")

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        current_result = ExecutionResult(
            exit_code=0,
            stdout="Success: 100 items",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        # Custom criteria pass
        mock_check_criteria.return_value = True

        # Create config with custom criteria
        script_config = ScriptConfig(
            name="test",
            path=script,
            success_criteria={"contains": "Success"},
        )

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result, config=script_config)

        assert verification.status == "success"
        assert verification.custom_criteria_passed is True

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    @patch("lazarus.core.runner.check_custom_criteria")
    def test_verify_fix_with_custom_criteria_failed(
        self, mock_check_criteria, mock_compare, mock_run_script, tmp_path
    ):
        """Test verifying with custom criteria that fail."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        current_result = ExecutionResult(
            exit_code=0,
            stdout="hello",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        # Mock comparison showing same error pattern
        mock_comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.9,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        # Custom criteria fail
        mock_check_criteria.return_value = False

        script_config = ScriptConfig(
            name="test",
            path=script,
            success_criteria={"contains": "Success"},
        )

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result, config=script_config)

        assert verification.status == "same_error"
        assert verification.custom_criteria_passed is False

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    def test_verify_fix_with_script_config(self, mock_compare, mock_run_script, tmp_path):
        """Test verify_fix respects ScriptConfig settings."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")
        working_dir = tmp_path / "workdir"
        working_dir.mkdir()

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        current_result = ExecutionResult(
            exit_code=0,
            stdout="hello",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        # Create config with custom settings
        script_config = ScriptConfig(
            name="test",
            path=script,
            timeout=120,
            working_dir=working_dir,
        )

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result, config=script_config)

        # Verify run_script was called with correct parameters
        mock_run_script.assert_called_once()
        call_args = mock_run_script.call_args
        assert call_args[1]["timeout"] == 120
        assert call_args[1]["working_dir"] == working_dir

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    @patch.dict(os.environ, {"TEST_VAR": "test_value", "ANOTHER_VAR": "another"})
    def test_verify_fix_with_environment_vars(
        self, mock_compare, mock_run_script, tmp_path
    ):
        """Test verify_fix passes environment variables from config."""
        script = tmp_path / "test.py"
        script.write_text("import os; print(os.environ.get('TEST_VAR'))")

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        current_result = ExecutionResult(
            exit_code=0,
            stdout="test_value",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        # Create config requiring specific env vars
        script_config = ScriptConfig(
            name="test",
            path=script,
            environment=["TEST_VAR", "ANOTHER_VAR"],
        )

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result, config=script_config)

        # Verify environment was passed
        call_args = mock_run_script.call_args
        assert call_args[1]["env"] == {"TEST_VAR": "test_value", "ANOTHER_VAR": "another"}

    @patch("lazarus.core.runner.ScriptRunner.run_script")
    @patch("lazarus.core.runner.compare_errors")
    @patch.dict(os.environ, {"EXISTING_VAR": "exists"}, clear=True)
    def test_verify_fix_missing_environment_var(
        self, mock_compare, mock_run_script, tmp_path
    ):
        """Test verify_fix when required env var is missing."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        previous_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=0.5,
        )

        current_result = ExecutionResult(
            exit_code=0,
            stdout="hello",
            stderr="",
            duration=0.3,
        )
        mock_run_script.return_value = current_result

        mock_comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )
        mock_compare.return_value = mock_comparison

        # Config requires env var that doesn't exist
        script_config = ScriptConfig(
            name="test",
            path=script,
            environment=["MISSING_VAR", "EXISTING_VAR"],
        )

        runner = ScriptRunner(LazarusConfig())
        verification = runner.verify_fix(script, previous_result, config=script_config)

        # Should only pass existing vars
        call_args = mock_run_script.call_args
        assert call_args[1]["env"] == {"EXISTING_VAR": "exists"}


class TestDetermineVerificationStatus:
    """Tests for _determine_verification_status method."""

    def test_determine_status_timeout(self):
        """Test determining status for timeout."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=-1,  # Timeout exit code
            stdout="",
            stderr="[TIMEOUT]",
            duration=60.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.0,
            key_differences=[],
        )

        status = runner._determine_verification_status(result, comparison, None)
        assert status == "timeout"

    def test_determine_status_custom_criteria_success(self):
        """Test determining status when custom criteria pass."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )

        status = runner._determine_verification_status(result, comparison, True)
        assert status == "success"

    def test_determine_status_custom_criteria_failed_same_error(self):
        """Test determining status when custom criteria fail with same error."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=0,
            stdout="hello",
            stderr="",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.9,
            key_differences=[],
        )

        status = runner._determine_verification_status(result, comparison, False)
        assert status == "same_error"

    def test_determine_status_custom_criteria_failed_different_error(self):
        """Test determining status when custom criteria fail with different error."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=0,
            stdout="hello",
            stderr="",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.3,
            key_differences=["Different output"],
        )

        status = runner._determine_verification_status(result, comparison, False)
        assert status == "different_error"

    def test_determine_status_standard_success(self):
        """Test determining status for standard success (no custom criteria)."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=[],
        )

        status = runner._determine_verification_status(result, comparison, None)
        assert status == "success"

    def test_determine_status_standard_same_error(self):
        """Test determining status for same error (no custom criteria)."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.95,
            key_differences=[],
        )

        status = runner._determine_verification_status(result, comparison, None)
        assert status == "same_error"

    def test_determine_status_standard_different_error(self):
        """Test determining status for different error (no custom criteria)."""
        runner = ScriptRunner(LazarusConfig())

        result = ExecutionResult(
            exit_code=2,
            stdout="",
            stderr="Different error",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.3,
            key_differences=["Exit code changed"],
        )

        status = runner._determine_verification_status(result, comparison, None)
        assert status == "different_error"
