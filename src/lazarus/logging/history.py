"""Healing history tracking for Lazarus.

This module provides the HealingHistory class that tracks and persists
healing session results to disk, allowing users to review past healing
attempts and their outcomes.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lazarus.core.healer import HealingResult


@dataclass
class HistoryRecord:
    """Record of a single healing session.

    Attributes:
        id: Unique identifier for this healing session
        timestamp: ISO 8601 timestamp of when healing started
        script_path: Path to the script that was healed
        success: Whether healing was successful
        attempts_count: Number of healing attempts made
        duration: Total duration of healing process in seconds
        pr_url: URL of created pull request (if applicable)
        error_summary: Brief error message if healing failed
    """

    id: str
    timestamp: str
    script_path: str
    success: bool
    attempts_count: int
    duration: float
    pr_url: str | None = None
    error_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the record
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "script_path": self.script_path,
            "success": self.success,
            "attempts_count": self.attempts_count,
            "duration": self.duration,
            "pr_url": self.pr_url,
            "error_summary": self.error_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryRecord:
        """Create a HistoryRecord from a dictionary.

        Args:
            data: Dictionary containing record data

        Returns:
            HistoryRecord instance
        """
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            script_path=data["script_path"],
            success=data["success"],
            attempts_count=data["attempts_count"],
            duration=data["duration"],
            pr_url=data.get("pr_url"),
            error_summary=data.get("error_summary"),
        )


class HealingHistory:
    """Manages healing history tracking and persistence.

    Stores healing session results as JSON files in a history directory,
    allowing users to query past healing attempts and their outcomes.

    Attributes:
        history_dir: Directory where history records are stored
    """

    def __init__(self, history_dir: Path = Path(".lazarus-history")) -> None:
        """Initialize the healing history tracker.

        Args:
            history_dir: Directory to store history records (default: .lazarus-history)
        """
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def find_history_dir(cls, start_path: Path | None = None) -> Path | None:
        """Search for .lazarus-history directory starting from start_path and going up.

        This method searches for an existing .lazarus-history directory by walking
        up the directory tree from the starting path. This allows commands to find
        history records even when run from subdirectories.

        Args:
            start_path: Directory to start searching from (default: current working directory)

        Returns:
            Path to .lazarus-history directory if found, None otherwise

        Example:
            >>> history_dir = HealingHistory.find_history_dir()
            >>> if history_dir:
            ...     history = HealingHistory(history_dir)
            ... else:
            ...     history = HealingHistory()  # Create in current directory
        """
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()
        while current != current.parent:
            history_dir = current / ".lazarus-history"
            if history_dir.exists() and history_dir.is_dir():
                return history_dir
            current = current.parent

        return None

    def record(self, result: HealingResult, script_path: Path) -> str:
        """Record a healing session result.

        Args:
            result: HealingResult from a healing session
            script_path: Path to the script that was healed

        Returns:
            Unique record ID for this healing session

        Example:
            >>> history = HealingHistory()
            >>> record_id = history.record(result, Path("scripts/backup.py"))
            >>> print(f"Recorded as {record_id}")
        """
        # Generate unique ID
        record_id = str(uuid.uuid4())

        # Create timestamp
        timestamp = datetime.now(UTC).isoformat()

        # Create error summary if healing failed
        error_summary = None
        if not result.success:
            if result.error_message:
                # Truncate long error messages
                error_summary = (
                    result.error_message[:200] + "..."
                    if len(result.error_message) > 200
                    else result.error_message
                )
            else:
                error_summary = "Healing failed with unknown error"

        # Create history record
        record = HistoryRecord(
            id=record_id,
            timestamp=timestamp,
            script_path=str(script_path.resolve()),
            success=result.success,
            attempts_count=len(result.attempts),
            duration=result.duration,
            pr_url=result.pr_url,
            error_summary=error_summary,
        )

        # Write to file
        record_file = self.history_dir / f"{record_id}.json"
        record_file.write_text(json.dumps(record.to_dict(), indent=2))

        return record_id

    def get_history(
        self,
        limit: int = 10,
        script_filter: str | None = None,
    ) -> list[HistoryRecord]:
        """Get healing history records.

        Args:
            limit: Maximum number of records to return (default: 10)
            script_filter: Optional script name or path to filter by

        Returns:
            List of HistoryRecord objects, sorted by timestamp (newest first)

        Example:
            >>> history = HealingHistory()
            >>> recent = history.get_history(limit=5)
            >>> for record in recent:
            ...     print(f"{record.timestamp}: {record.script_path}")
        """
        # Get all JSON files in history directory
        record_files = list(self.history_dir.glob("*.json"))

        # Load records
        records: list[HistoryRecord] = []
        for record_file in record_files:
            try:
                data = json.loads(record_file.read_text())
                record = HistoryRecord.from_dict(data)

                # Apply script filter if specified
                if script_filter:
                    # Match by filename or full path
                    script_path = Path(record.script_path)
                    if (
                        script_filter.lower() not in script_path.name.lower()
                        and script_filter.lower() not in str(script_path).lower()
                    ):
                        continue

                records.append(record)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip invalid record files
                continue

        # Sort by timestamp (newest first)
        records.sort(key=lambda r: r.timestamp, reverse=True)

        # Apply limit
        return records[:limit]

    def get_record(self, record_id: str) -> HistoryRecord | None:
        """Get a specific healing history record by ID.

        Args:
            record_id: Unique record ID

        Returns:
            HistoryRecord if found, None otherwise

        Example:
            >>> history = HealingHistory()
            >>> record = history.get_record("abc123...")
            >>> if record:
            ...     print(f"Success: {record.success}")
        """
        record_file = self.history_dir / f"{record_id}.json"

        if not record_file.exists():
            return None

        try:
            data = json.loads(record_file.read_text())
            return HistoryRecord.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def get_success_rate(self, script_filter: str | None = None) -> float:
        """Calculate success rate for healing sessions.

        Args:
            script_filter: Optional script name or path to filter by

        Returns:
            Success rate as a float between 0.0 and 1.0

        Example:
            >>> history = HealingHistory()
            >>> rate = history.get_success_rate()
            >>> print(f"Success rate: {rate * 100:.1f}%")
        """
        records = self.get_history(limit=1000, script_filter=script_filter)

        if not records:
            return 0.0

        successful = sum(1 for r in records if r.success)
        return successful / len(records)

    def cleanup_old_records(self, days: int = 30) -> int:
        """Remove healing history records older than specified days.

        Args:
            days: Number of days to keep (default: 30)

        Returns:
            Number of records removed

        Example:
            >>> history = HealingHistory()
            >>> removed = history.cleanup_old_records(days=7)
            >>> print(f"Removed {removed} old records")
        """
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)
        removed = 0

        for record_file in self.history_dir.glob("*.json"):
            try:
                data = json.loads(record_file.read_text())
                record_time = datetime.fromisoformat(data["timestamp"])

                if record_time < cutoff:
                    record_file.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                # Skip problematic files
                continue

        return removed
