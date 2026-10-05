"""
Dovi V1 — Core Agent

This is Dovi's brain. It takes user text, sends it to Google Gemini along
with the conversation history and system prompt, and returns Dovi's response.

Architecture notes:
  - The agent does NOT know about voice, avatar, or UI.
    It only deals with text in → text out.
  - It uses ConversationMemory to keep context across turns.
  - The system prompt (from prompts.py) is injected via Gemini's
    `system_instruction` parameter — Gemini treats it as persistent
    instructions that sit above the conversation.
  - In Phase 2 we'll add tool/function calling here.  The structure
    is designed so that's a small addition, not a rewrite.

Error handling:
  - If the API key is missing, we fail fast with a clear message.
  - If a Gemini API call fails, we catch it and return a friendly error
    instead of crashing the whole app.
"""

import logging
from google import genai
from google.genai import types

from app.config.settings import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.memory import ConversationMemory

logger = logging.getLogger("dovi.agent")


class DoviAgent:
    """
    The central Dovi agent.

    Usage:
        agent = DoviAgent()
        response = agent.chat("Hello!")
        print(response)   # "Hey there! How can I help?"
    """

    def __init__(self) -> None:
        # --- Validate API key ---
        if not settings.AI_API_KEY:
            raise ValueError(
                "AI_API_KEY is not set. Add it to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/apikey"
            )

        # --- Create the Gemini client ---
        # The `genai.Client` is the entry point to the Google GenAI SDK.
        # We pass the API key here; all subsequent calls use this client.
        self._client = genai.Client(api_key=settings.AI_API_KEY)
        self._model = settings.AI_MODEL

        # --- Conversation memory ---
        self._memory = ConversationMemory()

        logger.info(f"DoviAgent initialized with model: {self._model}")

    def chat(self, user_input: str) -> str:
        """
        Send a message to Dovi and get a response.

        Steps:
          1. Add the user's message to memory.
          2. Build the full conversation history.
          3. Call Gemini with the system prompt + history.
          4. Extract the response text.
          5. Add Dovi's response to memory.
          6. Return the response text.

        If the API call fails, we return a friendly error message
        instead of crashing.
        """
        if not user_input.strip():
            return "I didn't catch that. Could you say something?"

        # 1. Remember what the user said
        self._memory.add("user", user_input)
        logger.debug(f"User said: {user_input}")

        # 2. Build conversation contents for the API
        contents = self._memory.get_history()

        try:
            # 3. Call Gemini
            logger.info("Sending request to Gemini...")
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    # Temperature controls randomness.
                    # 0.7 = a good balance of creative but coherent.
                    temperature=0.7,
                    # max_output_tokens caps the response length.
                    max_output_tokens=500,
                ),
            )

            # 4. Extract text from the response
            reply = response.text.strip() if response.text else ""

            if not reply:
                logger.warning("Gemini returned an empty response.")
                reply = "Hmm, I drew a blank there. Could you try again?"

        except Exception as e:
            # 5. Handle API errors gracefully
            logger.error(f"Gemini API error: {e}")
            # Remove the user message we just added since we couldn't respond
            self._memory._messages.pop()
            return "I'm having trouble thinking right now. Try again in a moment."

        # 6. Remember Dovi's response
        self._memory.add("model", reply)
        logger.info(f"Dovi replied: {reply[:80]}...")

        return reply

    def reset(self) -> None:
        """Clear conversation history and start fresh."""
        self._memory.clear()
        logger.info("Conversation reset.")
