"""
Dovi V1 — Music Tool

Enables Dovi to control music playback (play, pause, resume, stop, volume).

Architecture:
  - MusicBackend: Interface defining player capabilities.
  - LocalSimulatedMusicPlayer: Default local V1 backend maintaining playback
    state and volume. Kept lightweight so it doesn't require heavy media libraries.
  - MusicTool: The tool registered with DoviAgent, exposing structured commands.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any, Callable
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger("dovi.tools.music")


@dataclass
class PlaybackState:
    """Current playback state."""

    is_playing: bool = False
    is_paused: bool = False
    current_track: str | None = None
    volume: int = 70  # 0 to 100


class MusicBackend(ABC):
    """Abstract interface for music playback providers (Local, MPD, Spotify, etc.)."""

    @abstractmethod
    def play(self, query: str | None = None) -> tuple[bool, str]:
        """Start or change playback."""
        pass

    @abstractmethod
    def pause(self) -> tuple[bool, str]:
        """Pause current track."""
        pass

    @abstractmethod
    def resume(self) -> tuple[bool, str]:
        """Resume paused track."""
        pass

    @abstractmethod
    def stop(self) -> tuple[bool, str]:
        """Stop playback completely."""
        pass

    @abstractmethod
    def set_volume(self, level: int) -> tuple[bool, str]:
        """Set volume level from 0 to 100."""
        pass

    @abstractmethod
    def get_status(self) -> PlaybackState:
        """Get current state."""
        pass


class LocalSimulatedMusicPlayer(MusicBackend):
    """
    Default local V1 music player.
    Keeps track of playback state and volume locally.
    Easily replaced with an external API (Spotify, YouTube Music) in future versions.
    """

    def __init__(self) -> None:
        self.state = PlaybackState()

    def play(self, query: str | None = None) -> tuple[bool, str]:
        track_name = query if query and query.strip() else "Focus Music"
        self.state.is_playing = True
        self.state.is_paused = False
        self.state.current_track = track_name
        return True, f"Now playing '{track_name}' at volume {self.state.volume}%"

    def pause(self) -> tuple[bool, str]:
        if not self.state.is_playing:
            return False, "No music is currently playing."
        if self.state.is_paused:
            return False, "Music is already paused."
        self.state.is_paused = True
        return True, f"Paused playback of '{self.state.current_track}'."

    def resume(self) -> tuple[bool, str]:
        if not self.state.is_playing:
            return self.play()
        if not self.state.is_paused:
            return False, "Music is already playing."
        self.state.is_paused = False
        return True, f"Resumed '{self.state.current_track}'."

    def stop(self) -> tuple[bool, str]:
        if not self.state.is_playing:
            return True, "Music is already stopped."
        track = self.state.current_track
        self.state.is_playing = False
        self.state.is_paused = False
        self.state.current_track = None
        return True, f"Stopped playing '{track}'."

    def set_volume(self, level: int) -> tuple[bool, str]:
        clamped = max(0, min(100, int(level)))
        self.state.volume = clamped
        return True, f"Volume set to {clamped}%."

    def get_status(self) -> PlaybackState:
        return self.state


class MusicTool(BaseTool):
    """Tool for controlling music playback."""

    def __init__(self, backend: MusicBackend | None = None) -> None:
        super().__init__()
        self.backend = backend or LocalSimulatedMusicPlayer()

    @property
    def name(self) -> str:
        return "music_tool"

    @property
    def description(self) -> str:
        return (
            "Control music playback. Supports: play, pause, resume, stop, "
            "set volume, and check playback status."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: 'play', 'pause', 'resume', 'stop', 'volume', or 'status'.",
                },
                "query": {
                    "type": "STRING",
                    "description": "Optional name of song, artist, or playlist to play (for action='play').",
                },
                "volume_level": {
                    "type": "INTEGER",
                    "description": "Volume percentage from 0 to 100 (for action='volume').",
                },
            },
            "required": ["action"],
        }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        action = kwargs.get("action", "").lower()
        valid_actions = ("play", "pause", "resume", "stop", "volume", "status")
        if action not in valid_actions:
            return False, f"Invalid music action '{action}'. Valid actions are: {', '.join(valid_actions)}"

        if action == "volume":
            vol = kwargs.get("volume_level")
            if vol is None:
                return False, "Missing 'volume_level' for volume action."
            try:
                vol_int = int(vol)
                if not (0 <= vol_int <= 100):
                    return False, f"Volume level {vol_int} must be between 0 and 100."
            except (ValueError, TypeError):
                return False, "volume_level must be an integer between 0 and 100."

        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "").lower()

        if action == "play":
            ok, msg = self.backend.play(kwargs.get("query"))
            return ToolResult(success=ok, message=msg, data={"state": self.backend.get_status().__dict__})

        elif action == "pause":
            ok, msg = self.backend.pause()
            return ToolResult(success=ok, message=msg, data={"state": self.backend.get_status().__dict__})

        elif action == "resume":
            ok, msg = self.backend.resume()
            return ToolResult(success=ok, message=msg, data={"state": self.backend.get_status().__dict__})

        elif action == "stop":
            ok, msg = self.backend.stop()
            return ToolResult(success=ok, message=msg, data={"state": self.backend.get_status().__dict__})

        elif action == "volume":
            ok, msg = self.backend.set_volume(kwargs["volume_level"])
            return ToolResult(success=ok, message=msg, data={"state": self.backend.get_status().__dict__})

        elif action == "status":
            st = self.backend.get_status()
            if st.is_playing:
                paused_str = " (Paused)" if st.is_paused else ""
                msg = f"Playing: '{st.current_track}'{paused_str} at volume {st.volume}%"
            else:
                msg = f"Music is stopped. Volume: {st.volume}%"
            return ToolResult(success=True, message=msg, data={"state": st.__dict__})

        return ToolResult(success=False, message=f"Unsupported action: {action}")

    def get_callable(self) -> Callable[..., dict[str, Any]]:
        tool_self = self

        def music_tool(
            action: str,
            query: str | None = None,
            volume_level: int | None = None,
        ) -> dict[str, Any]:
            """Control music playback.

            Args:
                action: 'play', 'pause', 'resume', 'stop', 'volume', or 'status'.
                query: Optional track, genre or song description to play.
                volume_level: Integer volume from 0 to 100 when action is 'volume'.
            """
            result = tool_self.safe_execute(
                action=action,
                query=query,
                volume_level=volume_level,
            )
            return result.to_dict()

        return music_tool
