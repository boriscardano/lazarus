"""Structured JSON logging for Lazarus healing sessions.

This module provides the LazarusLogger class that implements structured logging
with JSON formatting for file output and rich formatting for console output.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.logging import RichHandler

from lazarus.config.schema import LoggingConfig
from lazarus.core.healer import HealingResult


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured log output to files.

    Formats log records as single-line JSON objects with consistent structure:
    - timestamp: ISO 8601 timestamp with timezone
    - level: Log level name (DEBUG, INFO, WARNING, ERROR)
    - event_type: Type of event (healing_start, healing_attempt, etc.)
    - message: Human-readable message
    - Additional fields based on event type
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: LogRecord to format

        Returns:
            JSON string representing the log record
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields from record
        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "script_path"):
            log_data["script_path"] = str(record.script_path)
        if hasattr(record, "details"):
            log_data["details"] = record.details

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class LazarusLogger:
    """Structured logger for Lazarus healing sessions.

    Provides specialized logging methods for different healing events with
    both JSON file output and rich console output.

    Attributes:
        config: Logging configuration
        logger: Underlying Python logger instance
        console: Rich console for formatted output
    """

    def __init__(self, config: LoggingConfig) -> None:
        """Initialize the Lazarus logger.

        Args:
            config: Logging configuration from lazarus.yaml
        """
        self.config = config
        self.console = Console(stderr=True)

        # Create logger
        self.logger = logging.getLogger("lazarus")
        self.logger.setLevel(getattr(logging, config.level))

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Add file handler if file path is specified
        if config.file:
            self._add_file_handler(config)

        # Add console handler if enabled
        if config.console:
            self._add_console_handler(config)

    def _add_file_handler(self, config: LoggingConfig) -> None:
        """Add file handler with JSON formatting.

        Args:
            config: Logging configuration
        """
        log_file = Path(config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine handler type based on rotation config
        if config.rotation > 0:
            # Size-based rotation
            max_bytes = config.rotation * 1024 * 1024  # Convert MB to bytes
            handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=config.retention,
                encoding="utf-8",
            )
        else:
            # No rotation
            handler = logging.FileHandler(log_file, encoding="utf-8")

        # Use JSON formatter for file output
        handler.setFormatter(JSONFormatter())
        handler.setLevel(getattr(logging, config.level))
        self.logger.addHandler(handler)

    def _add_console_handler(self, config: LoggingConfig) -> None:
        """Add console handler with rich formatting.

        Args:
            config: Logging configuration
        """
        handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
        )
        handler.setLevel(getattr(logging, config.level))
        self.logger.addHandler(handler)

    def log_healing_start(
        self,
        script_path: Path,
        max_attempts: int,
        timeout: int,
    ) -> None:
        """Log the start of a healing session.

        Args:
            script_path: Path to the script being healed
            max_attempts: Maximum number of healing attempts
            timeout: Total timeout in seconds
        """
        self.logger.info(
            f"Starting healing session for {script_path.name}",
            extra={
                "event_type": "healing_start",
                "script_path": script_path,
                "details": {
                    "max_attempts": max_attempts,
                    "timeout": timeout,
                },
            },
        )

    def log_healing_attempt(
        self,
        script_path: Path,
        attempt_number: int,
        max_attempts: int,
    ) -> None:
        """Log a healing attempt.

        Args:
            script_path: Path to the script being healed
            attempt_number: Current attempt number (1-indexed)
            max_attempts: Maximum number of attempts
        """
        self.logger.info(
            f"Healing attempt {attempt_number}/{max_attempts} for {script_path.name}",
            extra={
                "event_type": "healing_attempt",
                "script_path": script_path,
                "details": {
                    "attempt_number": attempt_number,
                    "max_attempts": max_attempts,
                },
            },
        )

    def log_healing_complete(
        self,
        script_path: Path,
        result: HealingResult,
    ) -> None:
        """Log the completion of a healing session.

        Args:
            script_path: Path to the script that was healed
            result: Final healing result
        """
        level = logging.INFO if result.success else logging.ERROR
        status = "succeeded" if result.success else "failed"

        self.logger.log(
            level,
            f"Healing {status} for {script_path.name}",
            extra={
                "event_type": "healing_complete",
                "script_path": script_path,
                "details": {
                    "success": result.success,
                    "attempts": len(result.attempts),
                    "duration": result.duration,
                    "pr_url": result.pr_url,
                    "error_message": result.error_message,
                },
            },
        )

    def log_error(
        self,
        message: str,
        script_path: Optional[Path] = None,
        details: Optional[dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """Log an error message.

        Args:
            message: Error message
            script_path: Optional script path associated with the error
            details: Optional additional details
            exc_info: Whether to include exception traceback
        """
        extra: dict[str, Any] = {
            "event_type": "error",
        }
        if script_path:
            extra["script_path"] = script_path
        if details:
            extra["details"] = details

        self.logger.error(message, extra=extra, exc_info=exc_info)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            message: Debug message
            **kwargs: Additional fields to include in log
        """
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            message: Info message
            **kwargs: Additional fields to include in log
        """
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            message: Warning message
            **kwargs: Additional fields to include in log
        """
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            message: Error message
            exc_info: Whether to include exception traceback
            **kwargs: Additional fields to include in log
        """
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
