"""
Tests for Dovi Tools — Phase 2

Tests each of the 4 tools independently:
  1. TimerTool: duration validation, starting, checking status, cancelling.
  2. MusicTool: play, pause, resume, volume, status, validation.
  3. ReminderTool: sqlite persistence, adding, listing, completing.
  4. ComputerTool: strict whitelist enforcement, rejection of unauthorized apps/actions.
"""

import tempfile
from pathlib import Path
import pytest

from app.tools.base import BaseTool, ToolRegistry, ToolResult
from app.tools.timer import TimerTool
from app.tools.music import MusicTool, LocalSimulatedMusicPlayer
from app.tools.reminder import ReminderTool, ReminderStorage
from app.tools.computer import ComputerTool


class TestTimerTool:
    """Independent tests for TimerTool."""

    def test_start_timer_seconds(self):
        tool = TimerTool()
        res = tool.execute(action="start", duration_seconds=10, label="quick check")
        assert res.success is True
        assert "Started timer" in res.message
        assert res.data["duration_seconds"] == 10
        # Clean up
        tool.cancel_timer(res.data["timer_id"])

    def test_start_timer_minutes(self):
        tool = TimerTool()
        res = tool.execute(action="start", duration_minutes=1.5, label="tea")
        assert res.success is True
        assert res.data["duration_seconds"] == 90.0
        tool.cancel_timer(res.data["timer_id"])

    def test_invalid_duration(self):
        tool = TimerTool()
        res = tool.safe_execute(action="start", duration_seconds=-5)
        assert res.success is False
        assert "greater than 0" in res.message

    def test_timer_status_and_cancel(self):
        tool = TimerTool()
        start_res = tool.execute(action="start", duration_seconds=60, label="task")
        tid = start_res.data["timer_id"]

        status_res = tool.execute(action="status")
        assert status_res.success is True
        assert status_res.data["active_count"] >= 1

        cancel_res = tool.execute(action="cancel", timer_id=tid)
        assert cancel_res.success is True
        assert f"Cancelled timer #{tid}" in cancel_res.message


class TestMusicTool:
    """Independent tests for MusicTool."""

    def test_play_and_status(self):
        tool = MusicTool()
        res = tool.execute(action="play", query="Lofi Beats")
        assert res.success is True
        assert "Lofi Beats" in res.message

        status_res = tool.execute(action="status")
        assert status_res.success is True
        assert status_res.data["state"]["is_playing"] is True
        assert status_res.data["state"]["current_track"] == "Lofi Beats"

    def test_pause_and_resume(self):
        tool = MusicTool()
        tool.execute(action="play", query="Rock")
        pause_res = tool.execute(action="pause")
        assert pause_res.success is True
        assert pause_res.data["state"]["is_paused"] is True

        resume_res = tool.execute(action="resume")
        assert resume_res.success is True
        assert resume_res.data["state"]["is_paused"] is False

    def test_volume_control(self):
        tool = MusicTool()
        vol_res = tool.execute(action="volume", volume_level=85)
        assert vol_res.success is True
        assert vol_res.data["state"]["volume"] == 85

    def test_invalid_volume(self):
        tool = MusicTool()
        res = tool.safe_execute(action="volume", volume_level=150)
        assert res.success is False
        assert "between 0 and 100" in res.message


class TestReminderTool:
    """Independent tests for ReminderTool using a temporary SQLite DB."""

    def test_add_and_list_reminders(self, tmp_path: Path):
        db_file = tmp_path / "test_reminders.db"
        storage = ReminderStorage(db_path=db_file)
        tool = ReminderTool(storage=storage)

        add_res = tool.execute(action="add", text="Study ML", scheduled_time="7 PM")
        assert add_res.success is True
        assert add_res.data["id"] is not None

        list_res = tool.execute(action="list")
        assert list_res.success is True
        assert len(list_res.data["reminders"]) == 1
        assert list_res.data["reminders"][0]["text"] == "Study ML"

    def test_complete_reminder(self, tmp_path: Path):
        db_file = tmp_path / "test_reminders.db"
        storage = ReminderStorage(db_path=db_file)
        tool = ReminderTool(storage=storage)

        add_res = tool.execute(action="add", text="Workout", scheduled_time="6 AM")
        rem_id = add_res.data["id"]

        comp_res = tool.execute(action="complete", reminder_id=rem_id)
        assert comp_res.success is True

        # Now pending list should be empty
        list_res = tool.execute(action="list")
        assert len(list_res.data["reminders"]) == 0

    def test_empty_reminder_validation(self, tmp_path: Path):
        db_file = tmp_path / "test_reminders.db"
        storage = ReminderStorage(db_path=db_file)
        tool = ReminderTool(storage=storage)

        res = tool.safe_execute(action="add", text="", scheduled_time="tomorrow")
        assert res.success is False
        assert "cannot be empty" in res.message


class TestComputerTool:
    """Independent tests for ComputerTool and strict whitelist security."""

    def test_reject_unauthorized_application(self):
        tool = ComputerTool()
        # Attempting an arbitrary/dangerous command
        res = tool.safe_execute(action="open_application", application="rm -rf /")
        assert res.success is False
        assert "not in the whitelist" in res.message

    def test_reject_unauthorized_action(self):
        tool = ComputerTool()
        res = tool.safe_execute(action="execute_shell_script", application="vscode")
        assert res.success is False
        assert "not allowed" in res.message

    def test_allow_whitelisted_apps(self, monkeypatch):
        # Mock _launch so we don't actually spawn windows during tests
        tool = ComputerTool()
        monkeypatch.setattr(tool, "_launch", lambda app: (True, f"Launched {app}"))

        res = tool.safe_execute(action="open_application", application="vscode")
        assert res.success is True
        assert res.data["application"] == "vscode"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_list(self):
        registry = ToolRegistry()
        registry.register(TimerTool())
        registry.register(MusicTool())

        assert len(registry.list_tools()) == 2
        assert registry.get("timer_tool") is not None
        assert registry.get("music_tool") is not None
        assert len(registry.get_callables()) == 2
