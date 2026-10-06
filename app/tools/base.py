"""
Dovi V1 — Base Tool Abstraction

Defines the common interface that every Dovi tool must implement.

Architecture:
  - BaseTool: Abstract base class requiring name, description, schema, validate, execute.
  - ToolResult: Structured output of any tool execution (success, message, data).
  - safe_execute(): Wraps execute() with validation and try/except so tool errors
    never crash Dovi.
  - ToolRegistry: Manages registered tools, tracks tool execution results, and
    provides callables to the LLM agent.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
from typing import Any, Callable

logger = logging.getLogger("dovi.tools")


@dataclass
class ToolResult:
    """Structured result returned by every tool execution."""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for LLM context."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{status}] {self.message}"


class BaseTool(ABC):
    """
    Abstract base class for all Dovi tools.

    Subclasses must define:
      - name: Unique tool identifier (e.g. 'timer_tool')
      - description: Clear description of what the tool does
      - parameters: JSON schema defining expected input arguments
      - execute(**kwargs): The actual execution logic
    """

    def __init__(self) -> None:
        self._execution_listener: Callable[[str, ToolResult], None] | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description of the tool for the LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema of input parameters."""
        pass

    def set_execution_listener(self, listener: Callable[[str, ToolResult], None] | None) -> None:
        """Attach a listener invoked whenever this tool finishes executing."""
        self._execution_listener = listener

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """
        Validate input arguments before execution.
        Default implementation checks that required fields exist.
        Subclasses can override for domain-specific checks.
        """
        required = self.parameters.get("required", [])
        for req in required:
            if req not in kwargs or kwargs[req] is None:
                return False, f"Missing required parameter: '{req}'"
        return True, ""

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool with the validated arguments."""
        pass

    def safe_execute(self, **kwargs: Any) -> ToolResult:
        """
        Safely execute the tool with validation and error shielding.
        Never raises exceptions — returns a failed ToolResult instead.
        """
        logger.info(f"[AGENT] Selected tool: {self.name}")
        logger.info(f"[TOOL] Executing '{self.name}' with args: {kwargs}")

        # 1. Validation
        valid, err_msg = self.validate(**kwargs)
        if not valid:
            logger.warning(f"[TOOL] Validation failed for '{self.name}': {err_msg}")
            res = ToolResult(success=False, message=err_msg)
            if self._execution_listener:
                self._execution_listener(self.name, res)
            return res

        # 2. Execution with error handling
        try:
            result = self.execute(**kwargs)
            logger.info(f"[TOOL] '{self.name}' finished: {result}")
            if self._execution_listener:
                self._execution_listener(self.name, result)
            return result
        except Exception as e:
            logger.error(f"[TOOL] Exception in '{self.name}': {e}", exc_info=True)
            res = ToolResult(
                success=False,
                message=f"Error executing {self.name}: {str(e)}",
            )
            if self._execution_listener:
                self._execution_listener(self.name, res)
            return res

    @abstractmethod
    def get_callable(self) -> Callable[..., dict[str, Any]]:
        """
        Return a typed, documented callable function that Gemini's SDK
        can automatically inspect and use for function calling.
        """
        pass


class ToolRegistry:
    """Central registry holding all tools available to the Dovi agent."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self.last_result: ToolResult | None = None
        self.last_tool_name: str | None = None

    def _on_tool_executed(self, tool_name: str, result: ToolResult) -> None:
        self.last_tool_name = tool_name
        self.last_result = result

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        tool.set_execution_listener(self._on_tool_executed)
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return list of all registered tools."""
        return list(self._tools.values())

    def get_callables(self) -> list[Callable[..., dict[str, Any]]]:
        """Return list of callable functions for Gemini tools config."""
        return [tool.get_callable() for tool in self._tools.values()]

    def reset_turn(self) -> None:
        """Reset execution tracking for a new interaction turn."""
        self.last_result = None
        self.last_tool_name = None
