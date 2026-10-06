"""
Dovi V1 — Controlled Computer Actions Tool

Security-sensitive tool providing safe, strictly whitelisted operating system actions.

Security Rules (Section 13):
  1. Only predefined, whitelisted applications may be launched.
  2. Never allow arbitrary shell commands.
  3. Never use raw os.system(user_input) or unrestricted command execution.
  4. Non-whitelisted applications are explicitly rejected.
"""

import logging
import shutil
import subprocess
from typing import Any, Callable
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger("dovi.tools.computer")

# Whitelist definition: maps normalized alias -> list of command fallbacks
# Every command is executed via subprocess.Popen with a fixed list of arguments (NO shell=True)
ALLOWED_APPLICATIONS: dict[str, list[list[str]]] = {
    "vscode": [["code"]],
    "code": [["code"]],
    "browser": [
        ["google-chrome"],
        ["chromium-browser"],
        ["firefox"],
        ["xdg-open", "https://google.com"],
    ],
    "chrome": [["google-chrome"], ["chromium-browser"]],
    "firefox": [["firefox"]],
    "terminal": [
        ["gnome-terminal"],
        ["x-terminal-emulator"],
        ["konsole"],
        ["xfce4-terminal"],
        ["xterm"],
    ],
    "calculator": [["gnome-calculator"], ["kcalc"], ["xcalc"]],
    "file_manager": [["xdg-open", "."]],
}


class ComputerTool(BaseTool):
    """Tool for launching whitelisted desktop applications safely."""

    def __init__(self, whitelist: dict[str, list[list[str]]] | None = None) -> None:
        super().__init__()
        self.whitelist = whitelist or ALLOWED_APPLICATIONS

    @property
    def name(self) -> str:
        return "computer_tool"

    @property
    def description(self) -> str:
        return (
            "Open safe, predefined desktop applications (such as VS Code, browser, "
            "terminal, calculator, file manager). Only allowed applications can be launched."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action to perform: currently only 'open_application' is permitted.",
                },
                "application": {
                    "type": "STRING",
                    "description": (
                        "Name of the application to open. Allowed options: "
                        "'vscode', 'browser', 'chrome', 'firefox', 'terminal', 'calculator', 'file_manager'."
                    ),
                },
            },
            "required": ["action", "application"],
        }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        action = kwargs.get("action", "").lower()
        if action != "open_application":
            return False, f"Action '{action}' is not allowed. Only 'open_application' is supported."

        app_name = kwargs.get("application", "").strip().lower()
        if not app_name:
            return False, "Application name must be specified."

        if app_name not in self.whitelist:
            allowed_list = ", ".join(sorted(self.whitelist.keys()))
            return (
                False,
                f"Action rejected: '{app_name}' is not in the whitelist of allowed applications. "
                f"Allowed applications are: {allowed_list}.",
            )

        return True, ""

    def _launch(self, app_key: str) -> tuple[bool, str]:
        """Try launching the configured binary options for the whitelisted app."""
        candidates = self.whitelist[app_key]

        for cmd in candidates:
            binary = cmd[0]
            # Check if binary is installed on system
            if shutil.which(binary):
                try:
                    # Spawn detached process safely without shell injection
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    logger.info(f"[COMPUTER] Successfully launched: {cmd}")
                    return True, f"Launched {app_key} successfully."
                except Exception as e:
                    logger.warning(f"[COMPUTER] Failed to spawn {cmd}: {e}")

        # If binary wasn't found on the system
        return (
            False,
            f"Could not open {app_key}: none of the required binaries ({', '.join(c[0] for c in candidates)}) were found on this computer.",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        app_name = kwargs["application"].strip().lower()
        ok, msg = self._launch(app_name)
        return ToolResult(
            success=ok,
            message=msg,
            data={"application": app_name, "launched": ok},
        )

    def get_callable(self) -> Callable[..., dict[str, Any]]:
        tool_self = self

        def computer_tool(
            action: str,
            application: str,
        ) -> dict[str, Any]:
            """Launch a whitelisted computer application.

            Args:
                action: Must be 'open_application'.
                application: Whitelisted name (e.g. 'vscode', 'browser', 'terminal', 'calculator').
            """
            result = tool_self.safe_execute(
                action=action,
                application=application,
            )
            return result.to_dict()

        return computer_tool
