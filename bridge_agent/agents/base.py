"""Base agent with system prompt, tools, and conversation loop."""

import json
from typing import Callable

from bridge_agent.llm.base import LLMProvider, LLMMessage, LLMResponse, ToolCall
from bridge_agent.tools.base import BaseTool, ToolResult
from bridge_agent.tools.registry import tools_to_dicts, find_tool
from bridge_agent.config import MAX_TOOL_ITERATIONS


class BaseAgent:
    """Base agent with system prompt + tool execution loop."""

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        provider: LLMProvider,
        tools: list[BaseTool],
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_text: Callable[[str], None] | None = None,
    ):
        self._name = name
        self._description = description
        self._system_prompt = system_prompt
        self._provider = provider
        self._tools = tools
        self._on_tool_call = on_tool_call
        self._on_text = on_text
        self._conversation: list[LLMMessage] = []
        self._total_tokens_in = 0
        self._total_tokens_out = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def conversation(self) -> list[LLMMessage]:
        return self._conversation

    @property
    def total_tokens(self) -> tuple[int, int]:
        return self._total_tokens_in, self._total_tokens_out

    def reset(self):
        """Clear conversation history."""
        self._conversation = []
        self._total_tokens_in = 0
        self._total_tokens_out = 0

    def _build_messages(self, user_input: str) -> list[LLMMessage]:
        """Build message list with system prompt + history + new input."""
        messages = [LLMMessage(role="system", content=self._system_prompt)]
        messages.extend(self._conversation)
        messages.append(LLMMessage(role="user", content=user_input))
        return messages

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = find_tool(self._tools, tool_call.name)
        if not tool:
            return ToolResult(
                success=False, output="",
                error=f"Unknown tool: {tool_call.name}",
            )

        if self._on_tool_call:
            self._on_tool_call(tool_call.name, tool_call.arguments)

        return tool.execute(**tool_call.arguments)

    def chat(self, user_input: str) -> str:
        """Send a message and get a response, executing tools as needed."""
        self._conversation.append(LLMMessage(role="user", content=user_input))
        messages = [LLMMessage(role="system", content=self._system_prompt)]
        messages.extend(self._conversation)

        tool_dicts = tools_to_dicts(self._tools) if self._tools else None
        iteration = 0

        while iteration < MAX_TOOL_ITERATIONS:
            iteration += 1
            response = self._provider.chat(messages, tools=tool_dicts)
            self._total_tokens_in += response.tokens_in
            self._total_tokens_out += response.tokens_out

            if not response.has_tool_calls:
                # Final text response
                self._conversation.append(
                    LLMMessage(role="assistant", content=response.content)
                )
                if self._on_text and response.content:
                    self._on_text(response.content)
                return response.content

            # Process tool calls
            assistant_msg = LLMMessage(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
            self._conversation.append(assistant_msg)
            messages.append(assistant_msg)

            if response.content and self._on_text:
                self._on_text(response.content)

            for tc in response.tool_calls:
                result = self._execute_tool(tc)
                output = result.output if result.success else f"[ERROR] {result.error}\n{result.output}"

                tool_msg = LLMMessage(
                    role="tool",
                    content=output,
                    tool_call_id=tc.id,
                    name=tc.name,
                )
                self._conversation.append(tool_msg)
                messages.append(tool_msg)

        # Max iterations reached
        final = "Maximum tool iterations reached. Here's what I've done so far."
        self._conversation.append(LLMMessage(role="assistant", content=final))
        return final

    def chat_stream(self, user_input: str) -> str:
        """Stream response, handle tool calls. Returns final text."""
        # For streaming, we use the non-streaming chat with callbacks
        # (full streaming with tool loops is complex; this provides text callbacks)
        return self.chat(user_input)
