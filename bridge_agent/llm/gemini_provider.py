"""Google Gemini LLM provider."""

import json
from typing import Generator

from .base import LLMProvider, LLMMessage, LLMResponse, ToolCall

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    def name(self) -> str:
        return "gemini"

    def model_id(self) -> str:
        return self._model_name

    def available_models(self) -> list[str]:
        return GEMINI_MODELS

    def _build_tools(self, tools: list[dict] | None) -> list | None:
        """Convert our tool format to Gemini function declarations."""
        if not tools:
            return None

        declarations = []
        for tool in tools:
            decl = {
                "name": tool["name"],
                "description": tool.get("description", ""),
            }
            if "input_schema" in tool:
                schema = tool["input_schema"].copy()
                schema.pop("additionalProperties", None)
                decl["parameters"] = schema
            declarations.append(decl)

        return [{"function_declarations": declarations}]

    def _convert_messages(self, messages: list[LLMMessage]) -> tuple[str, list]:
        """Convert messages to Gemini format. Returns (system_instruction, history)."""
        system_text = ""
        history = []

        for msg in messages:
            if msg.role == "system":
                system_text += msg.content + "\n"
            elif msg.role == "user":
                history.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                parts = []
                if msg.content:
                    parts.append({"text": msg.content})
                for tc in msg.tool_calls:
                    parts.append({
                        "function_call": {
                            "name": tc.name,
                            "args": tc.arguments,
                        }
                    })
                if parts:
                    history.append({"role": "model", "parts": parts})
            elif msg.role == "tool":
                history.append({
                    "role": "user",
                    "parts": [{
                        "function_response": {
                            "name": msg.name or "tool",
                            "response": {"result": msg.content},
                        }
                    }],
                })

        return system_text.strip(), history

    def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None,
             temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse:
        system_instruction, history = self._convert_messages(messages)

        gen_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction if system_instruction else None,
            generation_config=gen_config,
            tools=self._build_tools(tools),
        )

        # Use history for multi-turn, send last user message
        chat_history = history[:-1] if history else []
        last_msg = history[-1] if history else {"role": "user", "parts": [{"text": "Hello"}]}

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(last_msg["parts"])

        return self._parse_response(response)

    def _parse_response(self, response) -> LLMResponse:
        text_parts = []
        tool_calls = []

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append(ToolCall(
                        id=f"gemini_{fc.name}_{id(fc)}",
                        name=fc.name,
                        arguments=args,
                    ))

        # Gemini doesn't provide token counts directly in all cases
        tokens_in = getattr(response, "usage_metadata", None)
        tin = tokens_in.prompt_token_count if tokens_in and hasattr(tokens_in, "prompt_token_count") else 0
        tout = tokens_in.candidates_token_count if tokens_in and hasattr(tokens_in, "candidates_token_count") else 0

        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            tokens_in=tin,
            tokens_out=tout,
            stop_reason="end_turn",
            model=self._model_name,
        )

    def chat_stream(self, messages: list[LLMMessage], tools: list[dict] | None = None,
                    temperature: float = 0.3, max_tokens: int = 4096) -> Generator[str, None, LLMResponse]:
        system_instruction, history = self._convert_messages(messages)

        gen_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction if system_instruction else None,
            generation_config=gen_config,
            tools=self._build_tools(tools),
        )

        chat_history = history[:-1] if history else []
        last_msg = history[-1] if history else {"role": "user", "parts": [{"text": "Hello"}]}

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(last_msg["parts"], stream=True)

        text_parts = []
        tool_calls = []

        for chunk in response:
            for part in chunk.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                    yield part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=f"gemini_{fc.name}_{id(fc)}",
                        name=fc.name,
                        arguments=dict(fc.args) if fc.args else {},
                    ))

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            tokens_in=0,
            tokens_out=0,
            stop_reason="end_turn",
            model=self._model_name,
        )
