"""
Dovi V1 — Application Entry Point

This is the bootstrap module. It:
  1. Configures logging for the whole application.
  2. Prints the startup banner.
  3. Will later initialize the agent, voice, avatar, and UI subsystems.

Called by run.py at the project root.
"""

import logging
import sys

from app.config.settings import settings


def _setup_logging() -> None:
    """
    Configure structured logging for every Dovi module.

    Why a function?  So we call it exactly once, before anything else runs.
    The format includes a tag like [AGENT] or [VOICE] — each module creates
    its own logger with `logging.getLogger(__name__)`, and the tag is the
    logger name.
    """
    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    date_format = "%H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Module-level logger for main.py itself.
logger = logging.getLogger("dovi")


def run() -> None:
    """Start Dovi V1."""
    _setup_logging()

    logger.info("=" * 50)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("  Your AI Desktop Companion")
    logger.info("=" * 50)
    logger.info("")
    logger.info("Phase 0 — Project skeleton is alive!")
    logger.info(f"Project root : {settings.PROJECT_ROOT}")
    logger.info(f"Assets dir   : {settings.ASSETS_DIR}")
    logger.info(f"Data dir     : {settings.DATA_DIR}")
    logger.info(f"Log level    : {settings.LOG_LEVEL}")
    logger.info("")

    # ----- Subsystem status (will be filled in future phases) -----
    _print_status("Agent", False)
    _print_status("Voice  (STT)", False)
    _print_status("Voice  (TTS)", False)
    _print_status("Tools", False)
    _print_status("Avatar", False)
    _print_status("UI", False)

    logger.info("")
    logger.info("Dovi is ready to grow! Phase 0 complete. ✓")
    logger.info("Run 'python run.py' after each phase to verify.")


def _print_status(component: str, ready: bool) -> None:
    """Print a nice status line for a subsystem."""
    symbol = "✓" if ready else "✗"
    state = "ready" if ready else "not yet built"
    logger.info(f"  {symbol} {component:<14} — {state}")
