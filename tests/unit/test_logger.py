"""Unit tests for the LazarusLogger class."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

from lazarus.config.schema import LoggingConfig
from lazarus.core.healer import HealingResult
from lazarus.logging.logger import JSONFormatter, LazarusLogger


class TestJSONFormatter:
    """Test the JSON formatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Healing started",
            args=(),
            exc_info=None,
        )
        record.event_type = "healing_start"
        record.script_path = Path("/test/script.py")
        record.details = {"attempts": 3}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["event_type"] == "healing_start"
        assert data["script_path"] == "/test/script.py"
        assert data["details"]["attempts"] == 3


class TestLazarusLogger:
    """Test the LazarusLogger class."""

    def test_init_console_only(self, tmp_path):
        """Test initialization with console logging only."""
        config = LoggingConfig(
            level="INFO",
            console=True,
            file=None,
        )
        logger = LazarusLogger(config)

        assert logger.logger.level == logging.INFO
        assert len(logger.logger.handlers) == 1

    def test_init_file_only(self, tmp_path):
        """Test initialization with file logging only."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="DEBUG",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        assert logger.logger.level == logging.DEBUG
        assert len(logger.logger.handlers) == 1
        assert log_file.parent.exists()

    def test_init_both_handlers(self, tmp_path):
        """Test initialization with both console and file handlers."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=True,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        assert len(logger.logger.handlers) == 2

    def test_log_healing_start(self, tmp_path):
        """Test logging healing start."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        script_path = Path("/test/script.py")
        logger.log_healing_start(
            script_path=script_path,
            max_attempts=3,
            timeout=300,
        )

        # Check log file contents
        log_contents = log_file.read_text()
        log_data = json.loads(log_contents.strip())

        assert log_data["level"] == "INFO"
        assert log_data["event_type"] == "healing_start"
        assert log_data["script_path"] == str(script_path)
        assert log_data["details"]["max_attempts"] == 3
        assert log_data["details"]["timeout"] == 300

    def test_log_healing_attempt(self, tmp_path):
        """Test logging healing attempt."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        script_path = Path("/test/script.py")
        logger.log_healing_attempt(
            script_path=script_path,
            attempt_number=2,
            max_attempts=3,
        )

        # Check log file contents
        log_contents = log_file.read_text()
        log_data = json.loads(log_contents.strip())

        assert log_data["event_type"] == "healing_attempt"
        assert log_data["details"]["attempt_number"] == 2
        assert log_data["details"]["max_attempts"] == 3

    def test_log_healing_complete_success(self, tmp_path):
        """Test logging successful healing completion."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        # Create a mock successful result
        result = MagicMock(spec=HealingResult)
        result.success = True
        result.attempts = []
        result.duration = 45.3
        result.pr_url = "https://github.com/user/repo/pull/1"
        result.error_message = None

        script_path = Path("/test/script.py")
        logger.log_healing_complete(script_path=script_path, result=result)

        # Check log file contents
        log_contents = log_file.read_text()
        log_data = json.loads(log_contents.strip())

        assert log_data["level"] == "INFO"
        assert log_data["event_type"] == "healing_complete"
        assert log_data["details"]["success"] is True
        assert log_data["details"]["duration"] == 45.3
        assert log_data["details"]["pr_url"] == "https://github.com/user/repo/pull/1"

    def test_log_healing_complete_failure(self, tmp_path):
        """Test logging failed healing completion."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        # Create a mock failed result
        result = MagicMock(spec=HealingResult)
        result.success = False
        result.attempts = []
        result.duration = 120.5
        result.pr_url = None
        result.error_message = "Failed after 3 attempts"

        script_path = Path("/test/script.py")
        logger.log_healing_complete(script_path=script_path, result=result)

        # Check log file contents
        log_contents = log_file.read_text()
        log_data = json.loads(log_contents.strip())

        assert log_data["level"] == "ERROR"
        assert log_data["details"]["success"] is False
        assert log_data["details"]["error_message"] == "Failed after 3 attempts"

    def test_log_error(self, tmp_path):
        """Test logging an error."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=0,
        )
        logger = LazarusLogger(config)

        logger.log_error(
            message="Test error",
            script_path=Path("/test/script.py"),
            details={"code": 1},
        )

        # Check log file contents
        log_contents = log_file.read_text()
        log_data = json.loads(log_contents.strip())

        assert log_data["level"] == "ERROR"
        assert log_data["event_type"] == "error"
        assert log_data["message"] == "Test error"
        assert log_data["details"]["code"] == 1

    def test_rotation_file_handler(self, tmp_path):
        """Test file handler with rotation enabled."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            console=False,
            file=log_file,
            rotation=10,  # 10 MB
            retention=5,
        )
        logger = LazarusLogger(config)

        # Verify handler is RotatingFileHandler
        from logging.handlers import RotatingFileHandler

        file_handler = logger.logger.handlers[0]
        assert isinstance(file_handler, RotatingFileHandler)
        assert file_handler.maxBytes == 10 * 1024 * 1024
        assert file_handler.backupCount == 5
