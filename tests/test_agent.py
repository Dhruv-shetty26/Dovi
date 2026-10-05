"""
Tests for the Dovi Agent — Phase 1

These tests verify the agent's internal components WITHOUT needing a real
API key or network access.  We test:
  - ConversationMemory works correctly
  - DoviAgent fails cleanly with no API key
  - The system prompt exists and is non-empty

We do NOT test live Gemini API calls here — that's what the manual test
commands are for (you type "Hello Dovi" in the terminal and see if it works).
"""

import pytest

from app.agent.memory import ConversationMemory, Message
from app.agent.prompts import SYSTEM_PROMPT


class TestConversationMemory:
    """Tests for the ConversationMemory class."""

    def test_add_and_retrieve(self):
        """Messages should be stored and retrievable."""
        mem = ConversationMemory()
        mem.add("user", "Hello")
        mem.add("model", "Hi there!")

        history = mem.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["parts"] == [{"text": "Hello"}]
        assert history[1]["role"] == "model"
        assert history[1]["parts"] == [{"text": "Hi there!"}]

    def test_empty_memory(self):
        """Fresh memory should return an empty list."""
        mem = ConversationMemory()
        assert mem.get_history() == []
        assert len(mem) == 0

    def test_trimming(self):
        """Memory should drop old messages when it exceeds max_messages."""
        mem = ConversationMemory(max_messages=4)

        # Add 6 messages (exceeds cap of 4)
        for i in range(6):
            role = "user" if i % 2 == 0 else "model"
            mem.add(role, f"Message {i}")

        # Should only keep the last 4
        assert len(mem) == 4
        history = mem.get_history()
        assert history[0]["parts"] == [{"text": "Message 2"}]
        assert history[-1]["parts"] == [{"text": "Message 5"}]

    def test_clear(self):
        """Clear should wipe all messages."""
        mem = ConversationMemory()
        mem.add("user", "Hello")
        mem.add("model", "Hi!")
        mem.clear()
        assert len(mem) == 0
        assert mem.get_history() == []


class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_prompt_exists(self):
        """The system prompt should not be empty."""
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT.strip()) > 50  # Should be substantial

    def test_prompt_mentions_dovi(self):
        """The system prompt should identify the AI as Dovi."""
        assert "Dovi" in SYSTEM_PROMPT


class TestDoviAgentInit:
    """Tests for DoviAgent initialization."""

    def test_fails_without_api_key(self, monkeypatch):
        """Agent should raise ValueError if AI_API_KEY is empty."""
        # Ensure the API key is empty
        from app.config.settings import settings
        original = settings.AI_API_KEY
        settings.AI_API_KEY = ""

        try:
            from app.agent.agent import DoviAgent
            with pytest.raises(ValueError, match="AI_API_KEY"):
                DoviAgent()
        finally:
            # Restore
            settings.AI_API_KEY = original
