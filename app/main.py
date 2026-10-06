"""
Dovi V1 — Application Entry Point

This is the bootstrap module. It:
  1. Configures logging for the whole application.
  2. Prints the startup banner.
  3. Runs the text chat loop (Phase 1).

Called by run.py at the project root.
"""

import logging
import sys

from app.config.settings import settings


def _setup_logging() -> None:
    """
    Configure structured logging for every Dovi module.

    Why a function?  So we call it exactly once, before anything else runs.
    The format includes a tag like [dovi.agent] or [dovi.memory] — each
    module creates its own logger with logging.getLogger(__name__) style names.
    """
    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    date_format = "%H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence noisy HTTP connection pool logs from third-party libraries
    for noisy_logger in ("httpcore", "httpx", "google", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


# Module-level logger for main.py itself.
logger = logging.getLogger("dovi")


def _print_banner() -> None:
    """Print the Dovi startup banner."""
    logger.info("=" * 50)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("  Your AI Desktop Companion")
    logger.info("=" * 50)
    logger.info("")


def _print_status(component: str, ready: bool) -> None:
    """Print a status line for a subsystem."""
    symbol = "✓" if ready else "✗"
    state = "ready" if ready else "not yet built"
    logger.info(f"  {symbol} {component:<14} — {state}")


def _text_chat_loop() -> None:
    """
    Phase 1 — Simple text chat in the terminal.

    This is a blocking loop that:
      1. Reads a line from the user.
      2. Sends it to the DoviAgent.
      3. Prints Dovi's response.
      4. Repeats until the user types 'exit' or 'quit'.

    Why import DoviAgent here (inside the function) instead of at the top?
      Because the agent validates the API key on init. If the key is missing,
      we want to show a clean error AFTER the banner, not a raw ImportError.
    """
    from app.agent.agent import DoviAgent

    try:
        agent = DoviAgent()
    except ValueError as e:
        logger.error(f"Cannot start agent: {e}")
        return

    print()
    print("💬 Dovi is ready! (Ask for timers, music, reminders, or apps. Type 'exit' to quit)")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            # User pressed Ctrl+C or Ctrl+D
            print("\nBye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("\nDovi: See you later! 👋")
            break

        if user_input.lower() == "reset":
            agent.reset()
            print("Dovi: Fresh start! What's up?")
            continue

        response = agent.chat(user_input)
        print(f"Dovi: {response}")
        print()


def run() -> None:
    """Start Dovi V1."""
    _setup_logging()
    _print_banner()

    # Subsystem status
    _print_status("Agent", True)
    _print_status("Voice  (STT)", False)
    _print_status("Voice  (TTS)", False)
    _print_status("Tools", True)
    _print_status("Avatar", False)
    _print_status("UI", False)
    logger.info("")

    # Launch the text chat loop
    _text_chat_loop()
