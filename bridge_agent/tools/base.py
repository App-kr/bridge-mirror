"""Base tool interface and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: str
    error: str = ""


class BaseTool(ABC):
    """Abstract tool that agents can invoke."""

    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM function calling."""
        ...

    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema for tool parameters."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        ...

    def to_dict(self) -> dict:
        """Convert to LLM tool definition format."""
        return {
            "name": self.name(),
            "description": self.description(),
            "input_schema": self.parameters_schema(),
        }
