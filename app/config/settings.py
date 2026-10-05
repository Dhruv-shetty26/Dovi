"""
Dovi V1 — Configuration Settings

Loads environment variables from .env and exposes them as a Settings object.
All configuration lives here so the rest of the app never touches os.environ directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# PROJECT_ROOT is the top-level Dovi/ directory (two levels up from this file).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
_dotenv_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=_dotenv_path)


class Settings:
    """
    Central configuration for Dovi V1.

    Every external key or tuneable value is read here once at import time.
    Components receive a Settings instance — they never read os.environ themselves.
    This keeps secrets in one place and makes testing easier (you can pass a
    fake Settings object).
    """

    # --- API Keys (filled from .env) ---
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    STT_API_KEY: str = os.getenv("STT_API_KEY", "")
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")

    # --- LLM ---
    # Which Gemini model to use. Updated to gemini-3.8-flash.
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-3.8-flash")

    # --- Application ---
    APP_NAME: str = "Dovi"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    # --- Paths ---
    PROJECT_ROOT: Path = PROJECT_ROOT
    ASSETS_DIR: Path = ASSETS_DIR
    DATA_DIR: Path = DATA_DIR


# A single shared instance so you can do:
#   from app.config.settings import settings
settings = Settings()
