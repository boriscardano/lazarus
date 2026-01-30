"""Unit tests for verification functionality."""

from __future__ import annotations

from lazarus.core.context import ExecutionResult
from lazarus.core.verification import (
    ErrorComparison,
    VerificationResult,
    check_custom_criteria,
    compare_errors,
)


class TestErrorComparison:
    """Tests for ErrorComparison dataclass."""

    def test_error_comparison_creation(self):
        """Test creating an ErrorComparison instance."""
        comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.95,
            key_differences=["Exit code changed from 1 to 0"],
        )
        assert comparison.is_same_error is True
        assert comparison.similarity_score == 0.95
        assert len(comparison.key_differences) == 1
        assert "Exit code changed" in comparison.key_differences[0]

    def test_error_comparison_empty_differences(self):
        """Test ErrorComparison with no differences."""
        comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=1.0,
            key_differences=[],
        )
        assert comparison.is_same_error is True
        assert comparison.similarity_score == 1.0
        assert comparison.key_differences == []

    def test_error_comparison_multiple_differences(self):
        """Test ErrorComparison with multiple differences."""
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.45,
            key_differences=[
                "Exit code changed from 1 to 2",
                "New error patterns appeared: TypeError",
                "Error patterns no longer present: ValueError",
            ],
        )
        assert comparison.is_same_error is False
        assert len(comparison.key_differences) == 3


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_success(self):
        """Test successful verification result."""
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.2,
            key_differences=["Exit code changed from 1 to 0"],
        )
        verification = VerificationResult(
            status="success",
            execution_result=exec_result,
            comparison=comparison,
            custom_criteria_passed=True,
        )
        assert verification.status == "success"
        assert verification.execution_result.success is True
        assert verification.custom_criteria_passed is True

    def test_verification_result_same_error(self):
        """Test verification result when same error occurs."""
        exec_result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="File not found",
            duration=0.5,
        )
        comparison = ErrorComparison(
            is_same_error=True,
            similarity_score=0.95,
            key_differences=[],
        )
        verification = VerificationResult(
            status="same_error",
            execution_result=exec_result,
            comparison=comparison,
            custom_criteria_passed=None,
        )
        assert verification.status == "same_error"
        assert verification.comparison.is_same_error is True
        assert verification.custom_criteria_passed is None

    def test_verification_result_different_error(self):
        """Test verification result with different error."""
        exec_result = ExecutionResult(
            exit_code=2,
            stdout="",
            stderr="Permission denied",
            duration=0.3,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.3,
            key_differences=["Exit code changed from 1 to 2", "New error patterns appeared: permission_denied"],
        )
        verification = VerificationResult(
            status="different_error",
            execution_result=exec_result,
            comparison=comparison,
            custom_criteria_passed=False,
        )
        assert verification.status == "different_error"
        assert verification.comparison.is_same_error is False

    def test_verification_result_timeout(self):
        """Test verification result for timeout."""
        exec_result = ExecutionResult(
            exit_code=124,
            stdout="",
            stderr="Timeout",
            duration=10.0,
        )
        comparison = ErrorComparison(
            is_same_error=False,
            similarity_score=0.1,
            key_differences=["New error patterns appeared: timeout"],
        )
        verification = VerificationResult(
            status="timeout",
            execution_result=exec_result,
            comparison=comparison,
            custom_criteria_passed=False,
        )
        assert verification.status == "timeout"


class TestCompareErrors:
    """Tests for compare_errors function."""

    def test_compare_identical_errors(self):
        """Test comparing two identical errors."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="FileNotFoundError: data.txt not found",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="FileNotFoundError: data.txt not found",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        assert comparison.is_same_error is True
        assert comparison.similarity_score > 0.9
        assert len(comparison.key_differences) == 0

    def test_compare_same_error_different_paths(self):
        """Test comparing same error with different file paths."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="FileNotFoundError: /home/user/data.txt not found",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="FileNotFoundError: /opt/app/data.txt not found",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should be considered same error due to normalization
        assert comparison.is_same_error is True
        assert comparison.similarity_score > 0.8

    def test_compare_different_exit_codes(self):
        """Test comparing errors with different exit codes."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error occurred",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=2,
            stdout="",
            stderr="Error occurred",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        assert "Exit code changed from 1 to 2" in comparison.key_differences
        # Even though exit codes differ, if stderr is identical and has error patterns,
        # it's still considered the same error (similarity > 0.6, same patterns)
        assert comparison.is_same_error is True

    def test_compare_different_error_types(self):
        """Test comparing different error types."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="FileNotFoundError: data.txt not found",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="TypeError: expected str, got int",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        assert comparison.is_same_error is False
        # Similarity can be around 0.6 due to common error keywords
        assert comparison.similarity_score < 0.7
        assert any("Error patterns no longer present" in diff for diff in comparison.key_differences)
        assert any("New error patterns appeared" in diff for diff in comparison.key_differences)

    def test_compare_errors_with_timestamps(self):
        """Test that timestamps are normalized in comparison."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error at 2024-01-30T12:34:56.789Z: Connection failed",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error at 2024-01-30T14:22:11.123Z: Connection failed",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should be same error after timestamp normalization
        assert comparison.is_same_error is True
        assert comparison.similarity_score > 0.8

    def test_compare_errors_with_process_ids(self):
        """Test that process IDs are normalized in comparison."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Process 12345 failed with error",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Process 67890 failed with error",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should be same error after PID normalization
        assert comparison.is_same_error is True
        assert comparison.similarity_score > 0.8

    def test_compare_errors_with_memory_addresses(self):
        """Test that memory addresses are normalized in comparison."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Segmentation fault at 0x7fff5fbff000",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Segmentation fault at 0x7fff5fbff999",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should be same error after memory address normalization
        assert comparison.is_same_error is True
        assert comparison.similarity_score > 0.8

    def test_compare_success_to_error(self):
        """Test comparing successful execution to error."""
        success = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )
        error = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error occurred",
            duration=0.5,
        )

        comparison = compare_errors(success, error)

        assert comparison.is_same_error is False
        assert "Exit code changed from 0 to 1" in comparison.key_differences

    def test_compare_empty_stderr(self):
        """Test comparing errors with empty stderr."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="Error in stdout",
            stderr="",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="Error in stdout",
            stderr="",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should still compare stdout
        assert comparison.similarity_score > 0.25  # stdout has 0.3 weight

    def test_compare_http_errors(self):
        """Test comparing HTTP error codes."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="HTTP 404: Resource not found",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="HTTP 404: Page not found",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Same HTTP error code and exit code
        assert comparison.is_same_error is True

    def test_compare_different_http_errors(self):
        """Test comparing different HTTP error codes."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="HTTP 404: Not found",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="HTTP 500: Internal server error",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Different HTTP errors
        assert comparison.is_same_error is False
        assert any("Error patterns no longer present" in diff for diff in comparison.key_differences)

    def test_compare_python_exceptions(self):
        """Test comparing Python exception types."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ValueError: invalid literal for int(): 'abc'",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="ValueError: invalid literal for int(): 'xyz'",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Same exception type
        assert comparison.is_same_error is True

    def test_compare_with_port_numbers(self):
        """Test that port numbers are normalized."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Connection refused on localhost:8080",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Connection refused on localhost:9090",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should be same error after port normalization
        assert comparison.is_same_error is True


class TestCheckCustomCriteria:
    """Tests for check_custom_criteria function."""

    def test_exit_code_criterion_pass(self):
        """Test exit code criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"exit_code": 0})

        assert passed is True

    def test_exit_code_criterion_fail(self):
        """Test exit code criterion fails."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"exit_code": 0})

        assert passed is False

    def test_contains_criterion_pass(self):
        """Test contains criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success: 100 items processed",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"contains": "Success"})

        assert passed is True

    def test_contains_criterion_fail(self):
        """Test contains criterion fails."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Completed",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"contains": "Success"})

        assert passed is False

    def test_not_contains_criterion_pass(self):
        """Test not_contains criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"not_contains": "Error"})

        assert passed is True

    def test_not_contains_criterion_fail_stdout(self):
        """Test not_contains criterion fails when pattern in stdout."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Warning: Error ignored",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"not_contains": "Error"})

        assert passed is False

    def test_not_contains_criterion_fail_stderr(self):
        """Test not_contains criterion fails when pattern in stderr."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="Warning: Error ignored",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"not_contains": "Error"})

        assert passed is False

    def test_regex_match_criterion_pass(self):
        """Test regex_match criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Processed 100 items successfully",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"regex_match": r"Processed \d+ items"})

        assert passed is True

    def test_regex_match_criterion_fail(self):
        """Test regex_match criterion fails."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Processing complete",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"regex_match": r"Processed \d+ items"})

        assert passed is False

    def test_regex_match_invalid_pattern(self):
        """Test regex_match with invalid pattern fails gracefully."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=1.0,
        )

        # Invalid regex pattern (unclosed bracket)
        passed = check_custom_criteria(result, {"regex_match": r"[invalid("})

        assert passed is False

    def test_stderr_contains_criterion_pass(self):
        """Test stderr_contains criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="Warning: deprecated function",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"stderr_contains": "Warning"})

        assert passed is True

    def test_stderr_contains_criterion_fail(self):
        """Test stderr_contains criterion fails."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Warning in stdout",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"stderr_contains": "Warning"})

        assert passed is False

    def test_stderr_not_contains_criterion_pass(self):
        """Test stderr_not_contains criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"stderr_not_contains": "Error"})

        assert passed is True

    def test_stderr_not_contains_criterion_fail(self):
        """Test stderr_not_contains criterion fails."""
        result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="Error: connection timeout",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {"stderr_not_contains": "Error"})

        assert passed is False

    def test_duration_less_than_criterion_pass(self):
        """Test duration_less_than criterion passes."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=2.5,
        )

        passed = check_custom_criteria(result, {"duration_less_than": 5.0})

        assert passed is True

    def test_duration_less_than_criterion_fail(self):
        """Test duration_less_than criterion fails."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=6.0,
        )

        passed = check_custom_criteria(result, {"duration_less_than": 5.0})

        assert passed is False

    def test_duration_less_than_exact_boundary(self):
        """Test duration_less_than at exact boundary (should fail)."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration=5.0,
        )

        passed = check_custom_criteria(result, {"duration_less_than": 5.0})

        assert passed is False  # >= fails the test

    def test_multiple_criteria_all_pass(self):
        """Test multiple criteria all passing."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success: 100 items processed",
            stderr="",
            duration=2.0,
        )

        criteria = {
            "exit_code": 0,
            "contains": "Success",
            "not_contains": "Error",
            "regex_match": r"\d+ items",
            "duration_less_than": 5.0,
        }

        passed = check_custom_criteria(result, criteria)

        assert passed is True

    def test_multiple_criteria_one_fails(self):
        """Test multiple criteria with one failure."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success: 100 items processed",
            stderr="",
            duration=2.0,
        )

        criteria = {
            "exit_code": 0,
            "contains": "Success",
            "not_contains": "items",  # This will fail
            "duration_less_than": 5.0,
        }

        passed = check_custom_criteria(result, criteria)

        assert passed is False

    def test_empty_criteria(self):
        """Test with empty criteria dictionary (should pass)."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0,
        )

        passed = check_custom_criteria(result, {})

        assert passed is True

    def test_criteria_with_numeric_values(self):
        """Test criteria with numeric values converted to string."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Version 1.2.3",
            stderr="",
            duration=1.0,
        )

        # Should handle numeric values by converting to string
        passed = check_custom_criteria(result, {"contains": 123})

        assert passed is False  # "123" not in "Version 1.2.3"

    def test_complex_regex_pattern(self):
        """Test complex regex pattern matching."""
        result = ExecutionResult(
            exit_code=0,
            stdout="User john.doe@example.com registered successfully",
            stderr="",
            duration=1.0,
        )

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        passed = check_custom_criteria(result, {"regex_match": email_pattern})

        assert passed is True

    def test_combined_stdout_stderr_criteria(self):
        """Test criteria checking both stdout and stderr."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Processing complete",
            stderr="Warning: deprecated API used",
            duration=1.0,
        )

        criteria = {
            "contains": "complete",  # In stdout
            "stderr_contains": "Warning",  # In stderr
            "not_contains": "Error",  # Not in either
            "stderr_not_contains": "Error",  # Not in stderr
        }

        passed = check_custom_criteria(result, criteria)

        assert passed is True


class TestCompareErrorsEdgeCases:
    """Additional edge case tests for error comparison."""

    def test_compare_permission_denied_errors(self):
        """Test comparing permission denied errors."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Permission denied: cannot access /etc/secret",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Permission denied: cannot access /var/log",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should recognize same error pattern
        assert comparison.is_same_error is True

    def test_compare_connection_refused_errors(self):
        """Test comparing connection refused errors."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Connection refused: cannot connect to database",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Connection refused: server not responding",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Both errors contain "connection refused" and "cannot connect"
        # but one has both patterns while the other doesn't
        assert "connection_refused" in str(comparison.key_differences).lower() or comparison.is_same_error is False

    def test_compare_timeout_errors(self):
        """Test comparing timeout errors."""
        error1 = ExecutionResult(
            exit_code=124,
            stdout="",
            stderr="Operation timeout after 30 seconds",
            duration=30.0,
        )
        error2 = ExecutionResult(
            exit_code=124,
            stdout="",
            stderr="Request timeout: server did not respond",
            duration=30.0,
        )

        comparison = compare_errors(error1, error2)

        # Should recognize same error pattern
        assert comparison.is_same_error is True

    def test_compare_no_such_file_errors(self):
        """Test comparing 'no such file' errors."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="No such file or directory: /tmp/data.txt",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="No such file: config.json",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should recognize same error pattern
        assert comparison.is_same_error is True

    def test_compare_cannot_connect_errors(self):
        """Test comparing 'cannot connect' errors."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Cannot connect to server at localhost:5432",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Cannot connect to database",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Should recognize same error pattern
        assert comparison.is_same_error is True

    def test_compare_mixed_error_phrases(self):
        """Test comparing errors with multiple common phrases."""
        error1 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="File not found and connection refused",
            duration=0.1,
        )
        error2 = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="File not found and cannot connect",
            duration=0.1,
        )

        comparison = compare_errors(error1, error2)

        # Both have "not_found" pattern but differ in connection error pattern
        # High similarity but different patterns detected
        assert comparison.similarity_score > 0.8
        assert len(comparison.key_differences) > 0
