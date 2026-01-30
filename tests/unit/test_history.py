"""Unit tests for the HealingHistory class."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lazarus.core.healer import HealingResult
from lazarus.logging.history import HealingHistory, HistoryRecord


class TestHistoryRecord:
    """Test the HistoryRecord dataclass."""

    def test_to_dict(self):
        """Test converting record to dictionary."""
        record = HistoryRecord(
            id="test-id",
            timestamp="2025-01-30T12:00:00Z",
            script_path="/test/script.py",
            success=True,
            attempts_count=2,
            duration=45.3,
            pr_url="https://github.com/user/repo/pull/1",
            error_summary=None,
        )

        data = record.to_dict()

        assert data["id"] == "test-id"
        assert data["success"] is True
        assert data["attempts_count"] == 2
        assert data["duration"] == 45.3
        assert data["pr_url"] == "https://github.com/user/repo/pull/1"
        assert data["error_summary"] is None

    def test_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            "id": "test-id",
            "timestamp": "2025-01-30T12:00:00Z",
            "script_path": "/test/script.py",
            "success": False,
            "attempts_count": 3,
            "duration": 120.5,
            "pr_url": None,
            "error_summary": "Failed after 3 attempts",
        }

        record = HistoryRecord.from_dict(data)

        assert record.id == "test-id"
        assert record.success is False
        assert record.attempts_count == 3
        assert record.error_summary == "Failed after 3 attempts"


class TestHealingHistory:
    """Test the HealingHistory class."""

    def test_init_creates_directory(self, tmp_path):
        """Test initialization creates history directory."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        assert history_dir.exists()
        assert history_dir.is_dir()

    def test_record_success(self, tmp_path):
        """Test recording a successful healing session."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create mock result
        result = MagicMock(spec=HealingResult)
        result.success = True
        result.attempts = [MagicMock(), MagicMock()]  # 2 attempts
        result.duration = 45.3
        result.pr_url = "https://github.com/user/repo/pull/1"
        result.error_message = None

        script_path = Path("/test/script.py")
        record_id = history.record(result=result, script_path=script_path)

        # Verify record ID is returned
        assert record_id is not None
        assert len(record_id) > 0

        # Verify file was created
        record_file = history_dir / f"{record_id}.json"
        assert record_file.exists()

        # Verify file contents
        data = json.loads(record_file.read_text())
        assert data["id"] == record_id
        assert data["success"] is True
        assert data["attempts_count"] == 2
        assert data["duration"] == 45.3
        assert data["pr_url"] == "https://github.com/user/repo/pull/1"
        assert data["error_summary"] is None

    def test_record_failure(self, tmp_path):
        """Test recording a failed healing session."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create mock result
        result = MagicMock(spec=HealingResult)
        result.success = False
        result.attempts = [MagicMock(), MagicMock(), MagicMock()]  # 3 attempts
        result.duration = 120.5
        result.pr_url = None
        result.error_message = "Failed to heal after 3 attempts"

        script_path = Path("/test/script.py")
        record_id = history.record(result=result, script_path=script_path)

        # Verify file contents
        record_file = history_dir / f"{record_id}.json"
        data = json.loads(record_file.read_text())

        assert data["success"] is False
        assert data["attempts_count"] == 3
        assert data["error_summary"] == "Failed to heal after 3 attempts"

    def test_record_truncates_long_error(self, tmp_path):
        """Test that long error messages are truncated."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create mock result with very long error
        long_error = "x" * 300
        result = MagicMock(spec=HealingResult)
        result.success = False
        result.attempts = [MagicMock()]
        result.duration = 60.0
        result.pr_url = None
        result.error_message = long_error

        record_id = history.record(result=result, script_path=Path("/test/script.py"))

        # Verify error was truncated
        record_file = history_dir / f"{record_id}.json"
        data = json.loads(record_file.read_text())

        assert len(data["error_summary"]) <= 203  # 200 + "..."
        assert data["error_summary"].endswith("...")

    def test_get_history_empty(self, tmp_path):
        """Test getting history when no records exist."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        records = history.get_history()

        assert len(records) == 0

    def test_get_history_returns_latest(self, tmp_path):
        """Test getting history returns latest records first."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create three records with different timestamps
        now = datetime.now(timezone.utc)
        records_data = [
            {
                "id": "old",
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "script_path": "/test/old.py",
                "success": True,
                "attempts_count": 1,
                "duration": 10.0,
            },
            {
                "id": "middle",
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "script_path": "/test/middle.py",
                "success": True,
                "attempts_count": 2,
                "duration": 20.0,
            },
            {
                "id": "new",
                "timestamp": now.isoformat(),
                "script_path": "/test/new.py",
                "success": False,
                "attempts_count": 3,
                "duration": 30.0,
            },
        ]

        for record_data in records_data:
            record_file = history_dir / f"{record_data['id']}.json"
            record_file.write_text(json.dumps(record_data))

        # Get history
        records = history.get_history(limit=10)

        # Verify order (newest first)
        assert len(records) == 3
        assert records[0].id == "new"
        assert records[1].id == "middle"
        assert records[2].id == "old"

    def test_get_history_with_limit(self, tmp_path):
        """Test getting history with limit."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create multiple records
        now = datetime.now(timezone.utc)
        for i in range(5):
            record_data = {
                "id": f"record-{i}",
                "timestamp": (now - timedelta(hours=i)).isoformat(),
                "script_path": f"/test/script{i}.py",
                "success": True,
                "attempts_count": 1,
                "duration": 10.0,
            }
            record_file = history_dir / f"{record_data['id']}.json"
            record_file.write_text(json.dumps(record_data))

        # Get history with limit
        records = history.get_history(limit=3)

        assert len(records) == 3

    def test_get_history_with_filter(self, tmp_path):
        """Test getting history with script filter."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create records for different scripts
        now = datetime.now(timezone.utc)
        records_data = [
            {
                "id": "backup-1",
                "timestamp": now.isoformat(),
                "script_path": "/test/backup.py",
                "success": True,
                "attempts_count": 1,
                "duration": 10.0,
            },
            {
                "id": "deploy-1",
                "timestamp": now.isoformat(),
                "script_path": "/test/deploy.py",
                "success": True,
                "attempts_count": 2,
                "duration": 20.0,
            },
            {
                "id": "backup-2",
                "timestamp": now.isoformat(),
                "script_path": "/test/backup.py",
                "success": False,
                "attempts_count": 3,
                "duration": 30.0,
            },
        ]

        for record_data in records_data:
            record_file = history_dir / f"{record_data['id']}.json"
            record_file.write_text(json.dumps(record_data))

        # Get history filtered by script
        records = history.get_history(limit=10, script_filter="backup")

        assert len(records) == 2
        for record in records:
            assert "backup" in record.script_path

    def test_get_record(self, tmp_path):
        """Test getting a specific record by ID."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create a record
        record_data = {
            "id": "test-id",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "script_path": "/test/script.py",
            "success": True,
            "attempts_count": 2,
            "duration": 45.3,
            "pr_url": "https://github.com/user/repo/pull/1",
        }
        record_file = history_dir / "test-id.json"
        record_file.write_text(json.dumps(record_data))

        # Get record
        record = history.get_record("test-id")

        assert record is not None
        assert record.id == "test-id"
        assert record.success is True
        assert record.attempts_count == 2

    def test_get_record_not_found(self, tmp_path):
        """Test getting a non-existent record."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        record = history.get_record("non-existent")

        assert record is None

    def test_get_success_rate(self, tmp_path):
        """Test calculating success rate."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create records: 3 successful, 2 failed
        now = datetime.now(timezone.utc)
        for i in range(5):
            record_data = {
                "id": f"record-{i}",
                "timestamp": now.isoformat(),
                "script_path": f"/test/script{i}.py",
                "success": i < 3,  # First 3 are successful
                "attempts_count": 1,
                "duration": 10.0,
            }
            record_file = history_dir / f"{record_data['id']}.json"
            record_file.write_text(json.dumps(record_data))

        # Calculate success rate
        rate = history.get_success_rate()

        assert rate == 0.6  # 3 out of 5

    def test_get_success_rate_empty(self, tmp_path):
        """Test success rate with no records."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        rate = history.get_success_rate()

        assert rate == 0.0

    def test_cleanup_old_records(self, tmp_path):
        """Test cleaning up old records."""
        history_dir = tmp_path / "history"
        history = HealingHistory(history_dir=history_dir)

        # Create old and new records
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(days=60)
        recent_time = now - timedelta(days=10)

        # Old record (should be removed)
        old_record = {
            "id": "old",
            "timestamp": old_time.isoformat(),
            "script_path": "/test/old.py",
            "success": True,
            "attempts_count": 1,
            "duration": 10.0,
        }
        (history_dir / "old.json").write_text(json.dumps(old_record))

        # Recent record (should be kept)
        recent_record = {
            "id": "recent",
            "timestamp": recent_time.isoformat(),
            "script_path": "/test/recent.py",
            "success": True,
            "attempts_count": 1,
            "duration": 10.0,
        }
        (history_dir / "recent.json").write_text(json.dumps(recent_record))

        # Cleanup records older than 30 days
        removed = history.cleanup_old_records(days=30)

        assert removed == 1
        assert not (history_dir / "old.json").exists()
        assert (history_dir / "recent.json").exists()

    def test_find_history_dir_in_current_directory(self, tmp_path):
        """Test finding history directory in current directory."""
        # Create history directory
        history_dir = tmp_path / ".lazarus-history"
        history_dir.mkdir()

        # Find from current directory
        found_dir = HealingHistory.find_history_dir(start_path=tmp_path)

        assert found_dir == history_dir

    def test_find_history_dir_in_parent_directory(self, tmp_path):
        """Test finding history directory in parent directory."""
        # Create history directory in parent
        history_dir = tmp_path / ".lazarus-history"
        history_dir.mkdir()

        # Create subdirectory structure
        subdir = tmp_path / "subdir" / "deep"
        subdir.mkdir(parents=True)

        # Find from subdirectory
        found_dir = HealingHistory.find_history_dir(start_path=subdir)

        assert found_dir == history_dir

    def test_find_history_dir_not_found(self, tmp_path):
        """Test finding history directory when none exists."""
        # Create subdirectory but no history directory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Try to find (should return None)
        found_dir = HealingHistory.find_history_dir(start_path=subdir)

        assert found_dir is None

    def test_find_history_dir_uses_cwd_by_default(self, tmp_path, monkeypatch):
        """Test finding history directory uses current working directory by default."""
        # Create history directory
        history_dir = tmp_path / ".lazarus-history"
        history_dir.mkdir()

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        # Find without specifying start_path
        found_dir = HealingHistory.find_history_dir()

        assert found_dir == history_dir

    def test_find_history_dir_only_matches_directories(self, tmp_path):
        """Test finding history directory only matches actual directories."""
        # Create a file (not a directory) named .lazarus-history
        fake_history = tmp_path / ".lazarus-history"
        fake_history.write_text("not a directory")

        # Try to find (should return None)
        found_dir = HealingHistory.find_history_dir(start_path=tmp_path)

        assert found_dir is None
