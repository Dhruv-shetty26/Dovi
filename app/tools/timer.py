"""
Dovi V1 — Timer Tool

Enables Dovi to start, monitor, and cancel timers locally in background threads.

Features:
  - Duration validation (supports minutes or seconds, must be > 0 and <= 24h)
  - Non-blocking background execution with threading.Timer
  - Completion notification callback / logging
  - Timer status query and cancellation support
"""

from dataclasses import dataclass, field
import datetime
import logging
import threading
from typing import Any, Callable
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger("dovi.tools.timer")


@dataclass
class ActiveTimer:
    """Represents a running background timer."""

    id: int
    duration_seconds: float
    label: str
    started_at: datetime.datetime
    ends_at: datetime.datetime
    thread: threading.Timer = field(repr=False)
    finished: bool = False
    cancelled: bool = False


class TimerTool(BaseTool):
    """Tool for setting, inspecting, and cancelling timers."""

    def __init__(self, on_timer_finished: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._timers: list[ActiveTimer] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._on_finished_callback = on_timer_finished

    @property
    def name(self) -> str:
        return "timer_tool"

    @property
    def description(self) -> str:
        return (
            "Start, check, or cancel a timer. Use this whenever the user asks to "
            "set a timer, check timer status, or cancel an active timer."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action to perform: 'start', 'status', or 'cancel'. Defaults to 'start'.",
                },
                "duration_minutes": {
                    "type": "NUMBER",
                    "description": "Timer duration in minutes (e.g. 25, 1.5). Required if action is 'start'.",
                },
                "duration_seconds": {
                    "type": "NUMBER",
                    "description": "Optional timer duration in seconds (e.g. 30). Used if seconds requested.",
                },
                "label": {
                    "type": "STRING",
                    "description": "Optional label or description for the timer (e.g. 'study break', 'boil eggs').",
                },
            },
            "required": ["action"],
        }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        action = kwargs.get("action", "start").lower()
        if action not in ("start", "status", "cancel"):
            return False, f"Invalid timer action '{action}'. Must be 'start', 'status', or 'cancel'."

        if action == "start":
            minutes = kwargs.get("duration_minutes")
            seconds = kwargs.get("duration_seconds")
            if minutes is None and seconds is None:
                return False, "Timer duration must be specified (in minutes or seconds)."

            total_sec = (float(minutes) * 60 if minutes is not None else 0.0) + (
                float(seconds) if seconds is not None else 0.0
            )

            if total_sec <= 0:
                return False, "Timer duration must be greater than 0."
            if total_sec > 86400:  # 24 hours
                return False, "Timer duration cannot exceed 24 hours."

        return True, ""

    def _on_timer_complete(self, timer_id: int) -> None:
        with self._lock:
            for t in self._timers:
                if t.id == timer_id and not t.cancelled:
                    t.finished = True
                    label_str = f" for '{t.label}'" if t.label else ""
                    msg = f"⏰ Timer #{t.id}{label_str} has finished!"
                    logger.info(f"[TIMER] {msg}")
                    if self._on_finished_callback:
                        self._on_finished_callback(msg)
                    break

    def start_timer(
        self,
        duration_minutes: float | None = None,
        duration_seconds: float | None = None,
        label: str = "",
    ) -> ToolResult:
        """Start a new timer for the specified duration."""
        sec = 0.0
        if duration_minutes is not None:
            sec += float(duration_minutes) * 60
        if duration_seconds is not None:
            sec += float(duration_seconds)

        now = datetime.datetime.now()
        ends_at = now + datetime.timedelta(seconds=sec)

        with self._lock:
            timer_id = self._next_id
            self._next_id += 1

            th = threading.Timer(sec, self._on_timer_complete, args=[timer_id])
            active = ActiveTimer(
                id=timer_id,
                duration_seconds=sec,
                label=label or "Timer",
                started_at=now,
                ends_at=ends_at,
                thread=th,
            )
            self._timers.append(active)
            th.daemon = True
            th.start()

        # Human-friendly duration string
        if sec >= 60:
            human_dur = f"{sec / 60:.1f} minute(s)" if sec % 60 != 0 else f"{int(sec // 60)} minute(s)"
        else:
            human_dur = f"{int(sec)} second(s)"

        msg = f"Started timer #{timer_id} for {human_dur}" + (f" ({label})" if label else "")
        return ToolResult(
            success=True,
            message=msg,
            data={
                "timer_id": timer_id,
                "duration_seconds": sec,
                "label": label,
                "ends_at": ends_at.isoformat(),
            },
        )

    def get_status(self) -> ToolResult:
        """Get the status of all active timers."""
        with self._lock:
            active = [t for t in self._timers if not t.finished and not t.cancelled]

        if not active:
            return ToolResult(
                success=True,
                message="No active timers right now.",
                data={"active_count": 0, "timers": []},
            )

        now = datetime.datetime.now()
        timer_info = []
        for t in active:
            remaining = max(0, int((t.ends_at - now).total_seconds()))
            timer_info.append(
                {
                    "id": t.id,
                    "label": t.label,
                    "remaining_seconds": remaining,
                    "remaining_display": f"{remaining // 60}m {remaining % 60}s",
                }
            )

        info_lines = [f"#{t['id']} '{t['label']}': {t['remaining_display']} left" for t in timer_info]
        return ToolResult(
            success=True,
            message=f"Active timers: {', '.join(info_lines)}",
            data={"active_count": len(active), "timers": timer_info},
        )

    def cancel_timer(self, timer_id: int | None = None) -> ToolResult:
        """Cancel a timer by ID or cancel the most recent active timer."""
        with self._lock:
            target = None
            if timer_id is not None:
                for t in self._timers:
                    if t.id == timer_id and not t.finished and not t.cancelled:
                        target = t
                        break
            else:
                for t in reversed(self._timers):
                    if not t.finished and not t.cancelled:
                        target = t
                        break

            if not target:
                return ToolResult(
                    success=False,
                    message="No matching active timer found to cancel.",
                )

            target.thread.cancel()
            target.cancelled = True

        return ToolResult(
            success=True,
            message=f"Cancelled timer #{target.id} ({target.label}).",
            data={"timer_id": target.id},
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "start").lower()
        if action == "start":
            return self.start_timer(
                duration_minutes=kwargs.get("duration_minutes"),
                duration_seconds=kwargs.get("duration_seconds"),
                label=kwargs.get("label", ""),
            )
        elif action == "status":
            return self.get_status()
        elif action == "cancel":
            return self.cancel_timer(timer_id=kwargs.get("timer_id"))
        return ToolResult(success=False, message=f"Unknown action: {action}")

    def get_callable(self) -> Callable[..., dict[str, Any]]:
        tool_self = self

        def timer_tool(
            action: str = "start",
            duration_minutes: float | None = None,
            duration_seconds: float | None = None,
            label: str = "",
            timer_id: int | None = None,
        ) -> dict[str, Any]:
            """Start, check, or cancel a timer.

            Args:
                action: 'start' to begin a timer, 'status' to check active timers, 'cancel' to stop one.
                duration_minutes: Timer duration in minutes (e.g. 25, 10, 1.5).
                duration_seconds: Optional timer duration in seconds (e.g. 30).
                label: Optional label describing the timer.
                timer_id: Timer ID to cancel (optional, cancels most recent if omitted).
            """
            result = tool_self.safe_execute(
                action=action,
                duration_minutes=duration_minutes,
                duration_seconds=duration_seconds,
                label=label,
                timer_id=timer_id,
            )
            return result.to_dict()

        return timer_tool
