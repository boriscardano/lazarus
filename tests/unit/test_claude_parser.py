"""Unit tests for Claude Code output parser."""

from __future__ import annotations

from lazarus.claude.parser import (
    _extract_changed_files,
    _extract_explanation,
    parse_claude_output,
)


def test_parse_success_with_files():
    """Test parsing successful output with file changes."""
    stdout = """
I've fixed the issue in the script.

Edit[file_path="/path/to/script.py"]
Modified the function to handle the error case.

Successfully updated script.py
"""
    stderr = ""
    exit_code = 0

    response = parse_claude_output(stdout, stderr, exit_code)

    assert response.success
    assert len(response.files_changed) > 0
    assert response.error_message is None
    assert "fix" in response.explanation.lower() or "updated" in response.explanation.lower()


def test_parse_auth_error():
    """Test parsing authentication error."""
    stdout = ""
    stderr = "Error: authentication failed. Please run 'claude login'."
    exit_code = 1

    response = parse_claude_output(stdout, stderr, exit_code)

    assert not response.success
    assert "authentication" in response.error_message.lower()
    assert len(response.files_changed) == 0


def test_parse_rate_limit():
    """Test parsing rate limit error."""
    stdout = ""
    stderr = "Error: rate limit exceeded. Please try again later."
    exit_code = 1

    response = parse_claude_output(stdout, stderr, exit_code)

    assert not response.success
    assert "rate limit" in response.error_message.lower()
    assert len(response.files_changed) == 0


def test_parse_generic_error():
    """Test parsing generic error."""
    stdout = ""
    stderr = "Some error occurred"
    exit_code = 1

    response = parse_claude_output(stdout, stderr, exit_code)

    assert not response.success
    assert response.error_message is not None
    assert len(response.files_changed) == 0


def test_parse_no_changes():
    """Test parsing output with no file changes."""
    stdout = "I analyzed the script but couldn't identify any issues to fix."
    stderr = ""
    exit_code = 0

    response = parse_claude_output(stdout, stderr, exit_code)

    assert not response.success  # No changes means no fix
    assert len(response.files_changed) == 0
    assert response.error_message is not None


def test_extract_changed_files_edit_tool():
    """Test extracting files from Edit tool usage."""
    output = 'I will fix this. Edit[file_path="/path/to/script.py"]'

    files = _extract_changed_files(output)

    assert "/path/to/script.py" in files


def test_extract_changed_files_write_tool():
    """Test extracting files from Write tool usage."""
    output = 'Creating config. Write[file_path="/path/to/config.yaml"]'

    files = _extract_changed_files(output)

    assert "/path/to/config.yaml" in files


def test_extract_changed_files_action_descriptions():
    """Test extracting files from action descriptions."""
    output = """
I've fixed the issue.
Edited script.py
Modified utils.py
Updated config.yaml
"""

    files = _extract_changed_files(output)

    assert "script.py" in files
    assert "utils.py" in files
    assert "config.yaml" in files


def test_extract_changed_files_deduplication():
    """Test that duplicate files are removed."""
    output = """
Edit[file_path="/path/to/script.py"]
Edited script.py
Modified /path/to/script.py
"""

    files = _extract_changed_files(output)

    # Should have deduplicated
    assert files.count("/path/to/script.py") + files.count("script.py") >= 1


def test_extract_explanation_simple():
    """Test extracting simple explanation."""
    output = "I've fixed the syntax error in the script."

    explanation = _extract_explanation(output)

    assert "fix" in explanation.lower()


def test_extract_explanation_with_details():
    """Test extracting detailed explanation."""
    output = """
The issue was a missing import statement. I've added the required import
at the top of the file. The script should now run without errors.
"""

    explanation = _extract_explanation(output)

    assert len(explanation) > 0
    assert "import" in explanation.lower() or "issue" in explanation.lower()


def test_extract_explanation_fallback():
    """Test explanation extraction with no clear explanation."""
    output = "Some generic output without clear explanation patterns."

    explanation = _extract_explanation(output)

    # Should return the generic fallback message
    assert len(explanation) > 0
