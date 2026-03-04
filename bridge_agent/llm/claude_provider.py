"""Anthropic Claude LLM provider."""

import json
from typing import Generator

from anthropic import Anthropic

from .base import LLMProvider, LLMMessage, LLMResponse, ToolCall

CLAUDE_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def name(self) -> str:
        return "claude"

    def model_id(self) -> str:
        return self._model

    def available_models(self) -> list[str]:
        return CLAUDE_MODELS

    def _build_params(self, messages: list[LLMMessage],
                      tools: list[dict] | None,
                      temperature: float, max_tokens: int) -> dict:
        """Build Anthropic API parameters from our message format."""
        system_text = ""
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_text += msg.content + "\n"
                continue

            if msg.role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }],
                })
                continue

            if msg.role == "assistant" and msg.tool_calls:
                content_blocks = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                api_messages.append({"role": "assistant", "content": content_blocks})
                continue

            api_messages.append({"role": msg.role, "content": msg.content})

        params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_text.strip():
            params["system"] = system_text.strip()
        if tools:
            params["tools"] = tools

        return params

    def _parse_response(self, response) -> LLMResponse:
        """Parse Anthropic response into LLMResponse."""
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            stop_reason=response.stop_reason or "",
            model=response.model,
        )

    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None,
             temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse:
        params = self._build_params(messages, tools, temperature, max_tokens)
        response = self._client.messages.create(**params)
        return self._parse_response(response)

    def chat_stream(self, messages: list[LLMMessage], tools: list[dict] | None = None,
                    temperature: float = 0.3, max_tokens: int = 4096) -> Generator[str, None, LLMResponse]:
        params = self._build_params(messages, tools, temperature, max_tokens)

        text_parts = []
        tool_calls = []
        current_tool_json = ""
        current_tool_id = ""
        current_tool_name = ""
        tokens_in = 0
        tokens_out = 0

        with self._client.messages.stream(**params) as stream:
            for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        block = event.content_block
                        if hasattr(block, "type") and block.type == "tool_use":
                            current_tool_id = block.id
                            current_tool_name = block.name
                            current_tool_json = ""
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            text_parts.append(delta.text)
                            yield delta.text
                        elif hasattr(delta, "partial_json"):
                            current_tool_json += delta.partial_json
                    elif event.type == "content_block_stop":
                        if current_tool_id:
                            try:
                                args = json.loads(current_tool_json) if current_tool_json else {}
                            except json.JSONDecodeError:
                                args = {}
                            tool_calls.append(ToolCall(
                                id=current_tool_id,
                                name=current_tool_name,
                                arguments=args,
                            ))
                            current_tool_id = ""
                            current_tool_name = ""
                            current_tool_json = ""
                    elif event.type == "message_delta":
                        if hasattr(event, "usage") and event.usage:
                            tokens_out = getattr(event.usage, "output_tokens", 0)
                    elif event.type == "message_start":
                        if hasattr(event, "message") and hasattr(event.message, "usage"):
                            tokens_in = event.message.usage.input_tokens

        final_response = LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            stop_reason="end_turn",
            model=self._model,
        )
        return final_response
