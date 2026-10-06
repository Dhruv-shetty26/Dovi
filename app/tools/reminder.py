"""
Dovi V1 — Reminder Tool

Enables Dovi to persist and manage reminders locally using SQLite.

Features:
  - Stores reminder text, scheduled time, creation timestamp, and status.
  - CRUD operations: add, list, complete, delete.
  - Zero cloud dependencies — pure local SQLite database.
"""

from dataclasses import dataclass
import datetime
import logging
from pathlib import Path
import sqlite3
from typing import Any, Callable
from app.config.settings import settings
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger("dovi.tools.reminder")


@dataclass
class Reminder:
    """Represents a reminder item."""

    id: int
    text: str
    scheduled_time: str
    status: str
    created_at: str


class ReminderStorage:
    """Manages SQLite storage for reminders."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = settings.DATA_DIR / "reminders.db"
        else:
            self.db_path = Path(db_path)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(self, text: str, scheduled_time: str) -> Reminder:
        created_at = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO reminders (text, scheduled_time, status, created_at) VALUES (?, ?, 'pending', ?)",
                (text, scheduled_time, created_at),
            )
            reminder_id = cur.lastrowid
        return Reminder(
            id=reminder_id,
            text=text,
            scheduled_time=scheduled_time,
            status="pending",
            created_at=created_at,
        )

    def list_all(self, status: str | None = None) -> list[Reminder]:
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT id, text, scheduled_time, status, created_at FROM reminders WHERE status = ? ORDER BY id DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, text, scheduled_time, status, created_at FROM reminders ORDER BY id DESC"
                ).fetchall()

        return [
            Reminder(
                id=r["id"],
                text=r["text"],
                scheduled_time=r["scheduled_time"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def mark_complete(self, reminder_id: int) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE reminders SET status = 'completed' WHERE id = ?",
                (reminder_id,),
            )
            return cur.rowcount > 0

    def delete(self, reminder_id: int) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            return cur.rowcount > 0


class ReminderTool(BaseTool):
    """Tool for creating and querying local reminders."""

    def __init__(self, storage: ReminderStorage | None = None) -> None:
        super().__init__()
        self.storage = storage or ReminderStorage()

    @property
    def name(self) -> str:
        return "reminder_tool"

    @property
    def description(self) -> str:
        return (
            "Add, list, or complete reminders. Use this whenever the user asks to "
            "be reminded of something at a specific time, asks to see their reminders, "
            "or wants to complete a reminder."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: 'add', 'list', or 'complete'. Defaults to 'add'.",
                },
                "text": {
                    "type": "STRING",
                    "description": "Reminder description or task (e.g. 'work on Dovi', 'study for exam').",
                },
                "scheduled_time": {
                    "type": "STRING",
                    "description": "When to remind the user (e.g. '7 PM', 'tomorrow at 9 AM', 'in 2 hours').",
                },
                "reminder_id": {
                    "type": "INTEGER",
                    "description": "ID of reminder to complete (for action='complete').",
                },
            },
            "required": ["action"],
        }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        action = kwargs.get("action", "add").lower()
        if action not in ("add", "list", "complete"):
            return False, f"Invalid reminder action '{action}'. Must be 'add', 'list', or 'complete'."

        if action == "add":
            if not kwargs.get("text", "").strip():
                return False, "Reminder text cannot be empty."
            if not kwargs.get("scheduled_time", "").strip():
                return False, "Scheduled time cannot be empty."

        elif action == "complete":
            if kwargs.get("reminder_id") is None:
                return False, "Missing 'reminder_id' for complete action."

        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "add").lower()

        if action == "add":
            text = kwargs["text"].strip()
            time_str = kwargs["scheduled_time"].strip()
            item = self.storage.add(text, time_str)
            msg = f"Reminder set: '{text}' for {time_str} (ID #{item.id})."
            return ToolResult(
                success=True,
                message=msg,
                data={"id": item.id, "text": item.text, "time": item.scheduled_time},
            )

        elif action == "list":
            items = self.storage.list_all(status="pending")
            if not items:
                return ToolResult(
                    success=True,
                    message="You have no pending reminders.",
                    data={"reminders": []},
                )

            summary = [f"#{r.id}: '{r.text}' at {r.scheduled_time}" for r in items]
            return ToolResult(
                success=True,
                message=f"Pending reminders:\n" + "\n".join(summary),
                data={"reminders": [r.__dict__ for r in items]},
            )

        elif action == "complete":
            rem_id = int(kwargs["reminder_id"])
            ok = self.storage.mark_complete(rem_id)
            if ok:
                return ToolResult(
                    success=True,
                    message=f"Reminder #{rem_id} marked as completed.",
                    data={"id": rem_id},
                )
            return ToolResult(
                success=False,
                message=f"No reminder found with ID #{rem_id}.",
            )

        return ToolResult(success=False, message=f"Unknown action: {action}")

    def get_callable(self) -> Callable[..., dict[str, Any]]:
        tool_self = self

        def reminder_tool(
            action: str = "add",
            text: str | None = None,
            scheduled_time: str | None = None,
            reminder_id: int | None = None,
        ) -> dict[str, Any]:
            """Create, view, or complete reminders.

            Args:
                action: 'add' to create, 'list' to view pending reminders, 'complete' to finish one.
                text: What to remember (e.g. 'work on Dovi').
                scheduled_time: When to remind (e.g. '7 PM', 'tomorrow 9 AM').
                reminder_id: ID of reminder when completing.
            """
            result = tool_self.safe_execute(
                action=action,
                text=text or "",
                scheduled_time=scheduled_time or "",
                reminder_id=reminder_id,
            )
            return result.to_dict()

        return reminder_tool
