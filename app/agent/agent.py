"""
Dovi V1 — Core Agent (Phase 2 with Tool System)

This is Dovi's brain. It receives user text, uses Google Gemini with structured
tool/function calling, executes requested actions, and returns natural-language replies.

Architecture:
  - ToolRegistry: Holds TimerTool, MusicTool, ReminderTool, ComputerTool.
  - Automatic Function Calling (AFC): Gemini decides if a tool is needed,
    generates structured arguments, and our tool abstraction executes safely.
  - Resilient Error Handling: Gracefully retries transient 503 errors and shields
    against tool failures.
  - State Tracking: Tracks last executed tool result for Avatar and UI updates.
"""

import logging
import time
from google import genai
from google.genai import types

from app.config.settings import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.memory import ConversationMemory
from app.tools.base import ToolRegistry, ToolResult
from app.tools.computer import ComputerTool
from app.tools.music import MusicTool
from app.tools.reminder import ReminderTool
from app.tools.timer import TimerTool

logger = logging.getLogger("dovi.agent")


class DoviAgent:
    """
    The central Dovi intelligent agent.

    Usage:
        agent = DoviAgent()
        response = agent.chat("Start a 25 minute timer.")
        print(response)  # "Timer started for 25 minutes!"
    """

    def __init__(self, model: str | None = None) -> None:
        if not settings.AI_API_KEY:
            raise ValueError(
                "AI_API_KEY is not set. Add it to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/apikey"
            )

        self._client = genai.Client(api_key=settings.AI_API_KEY)
        self._model = model or settings.AI_MODEL

        # --- Register Tools ---
        self.tools = ToolRegistry()
        self.tools.register(TimerTool())
        self.tools.register(MusicTool())
        self.tools.register(ReminderTool())
        self.tools.register(ComputerTool())

        # --- Memory and State Tracking ---
        self._memory = ConversationMemory()
        self.last_tool_name: str | None = None
        self.last_tool_result: ToolResult | None = None

        # --- Initialize Gemini Chat Session with Tools ---
        self._init_chat_session()

        logger.info(
            f"DoviAgent initialized with model '{self._model}' and {len(self.tools.list_tools())} tools."
        )

    def _init_chat_session(self) -> None:
        """Create or reset the Gemini chat session configured with our tools."""
        callables = self.tools.get_callables()
        self._chat = self._client.chats.create(
            model=self._model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=500,
                tools=callables,
            ),
        )

    def chat(self, user_input: str) -> str:
        """
        Process a user message:
          1. Record user turn in memory and reset turn tracking.
          2. Send message to Gemini.
          3. If a tool is needed, Gemini invokes it via our Tool abstraction.
          4. Return the final natural-language response.
        """
        clean_input = user_input.strip()
        if not clean_input:
            return "I didn't catch that. Could you say something?"

        logger.info(f"[AGENT] Processing request: '{clean_input}'")
        self._memory.add("user", clean_input)
        self.tools.reset_turn()
        self.last_tool_name = None
        self.last_tool_result = None

        reply = ""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self._chat.send_message(clean_input)
                reply = response.text.strip() if response.text else ""
                break
            except Exception as e:
                err_str = str(e)
                # Retry transient server errors (e.g. 503 high demand or temporary network glitches)
                if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 2
                    logger.warning(
                        f"[AGENT] Transient 503 from Gemini, retrying in {wait_sec}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(wait_sec)
                    continue

                logger.error(f"[AGENT] Gemini error: {e}")
                reply = "I'm having trouble thinking right now. Please try again in a moment."
                break

        if not reply:
            reply = "I'm here, but I didn't get a response. Could you try again?"

        # Update last tool executed during this turn
        self.last_tool_name = self.tools.last_tool_name
        self.last_tool_result = self.tools.last_result

        # Save model reply to memory
        self._memory.add("model", reply)
        logger.info(f"Dovi replied: {reply[:100]}...")

        return reply

    def reset(self) -> None:
        """Clear conversation history and re-initialize the chat session."""
        self._memory.clear()
        self.tools.reset_turn()
        self.last_tool_name = None
        self.last_tool_result = None
        self._init_chat_session()
        logger.info("Conversation reset.")
