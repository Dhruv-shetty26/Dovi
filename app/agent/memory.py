"""
Dovi V1 — Conversation Memory

Keeps track of the current conversation so Dovi remembers what was said
earlier in the session.

How it works:
  - Every message (from the user OR from Dovi) is appended to a list.
  - Each message has a "role" (either "user" or "model") and "content" (the text).
  - When we send a request to Gemini, we include the full conversation history
    so the LLM has context.
  - We cap the history at MAX_MESSAGES to avoid sending too many tokens.
    When the cap is hit, we drop the oldest messages (keeping the most recent).

Why "model" instead of "assistant"?
  Google Gemini's API uses "model" for the AI's messages (unlike OpenAI which
  uses "assistant"). We use Gemini's naming to keep things simple.

V1 scope:
  - In-memory only (lost when you restart Dovi)
  - Simple list of messages
  - No embeddings, no vector DB, no RAG
  - The architecture is ready for a smarter memory system later
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("dovi.memory")

# Maximum number of messages (user + model) we keep in history.
# Each user message + model reply = 2 messages, so 50 = ~25 exchanges.
MAX_MESSAGES = 50


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "model"
    content: str


class ConversationMemory:
    """
    Stores the running conversation between the user and Dovi.

    Usage:
        memory = ConversationMemory()
        memory.add("user", "Hello!")
        memory.add("model", "Hey there!")
        history = memory.get_history()   # → list of dicts for the API
    """

    def __init__(self, max_messages: int = MAX_MESSAGES) -> None:
        self._messages: list[Message] = []
        self._max_messages = max_messages

    def add(self, role: str, content: str) -> None:
        """Add a message and trim if we exceed the cap."""
        self._messages.append(Message(role=role, content=content))

        if len(self._messages) > self._max_messages:
            # Drop the oldest messages (keep the most recent ones).
            dropped = len(self._messages) - self._max_messages
            self._messages = self._messages[dropped:]
            logger.debug(f"Trimmed {dropped} old message(s) from memory.")

    def get_history(self) -> list[dict]:
        """
        Return the conversation history in the format Gemini expects.

        Returns a list of dicts like:
            [
                {"role": "user",  "parts": [{"text": "Hello!"}]},
                {"role": "model", "parts": [{"text": "Hey!"}]},
            ]
        """
        return [
            {"role": msg.role, "parts": [{"text": msg.content}]}
            for msg in self._messages
        ]

    def clear(self) -> None:
        """Wipe the conversation history."""
        self._messages.clear()
        logger.debug("Conversation memory cleared.")

    def __len__(self) -> int:
        return len(self._messages)
