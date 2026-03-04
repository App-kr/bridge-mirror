"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: dict


@dataclass
class LLMMessage:
    """A message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None  # for tool result messages
    name: str | None = None  # tool name for tool results


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    stop_reason: str = ""
    model: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None,
             temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse:
        """Send messages and get a complete response."""
        ...

    @abstractmethod
    def chat_stream(self, messages: list[LLMMessage], tools: list[dict] | None = None,
                    temperature: float = 0.3, max_tokens: int = 4096) -> Generator[str, None, LLMResponse]:
        """Stream response tokens. Yields text chunks, returns final LLMResponse."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'claude', 'gemini')."""
        ...

    @abstractmethod
    def model_id(self) -> str:
        """Current model identifier."""
        ...

    @abstractmethod
    def available_models(self) -> list[str]:
        """List of available model IDs for this provider."""
        ...
