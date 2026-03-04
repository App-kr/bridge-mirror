"""Provider factory — create LLM providers by name."""

from .base import LLMProvider
from .claude_provider import ClaudeProvider, CLAUDE_MODELS
from .gemini_provider import GeminiProvider, GEMINI_MODELS


PROVIDERS = {
    "claude": {
        "class": ClaudeProvider,
        "models": CLAUDE_MODELS,
        "key_name": "anthropic_api_key",
        "display": "Anthropic Claude",
    },
    "gemini": {
        "class": GeminiProvider,
        "models": GEMINI_MODELS,
        "key_name": "google_api_key",
        "display": "Google Gemini",
    },
}


def create_provider(provider_name: str, api_key: str,
                    model: str | None = None) -> LLMProvider:
    """Create an LLM provider by name."""
    info = PROVIDERS.get(provider_name)
    if not info:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    cls = info["class"]
    if model:
        return cls(api_key=api_key, model=model)
    return cls(api_key=api_key)


def list_providers() -> dict:
    """Return provider info for display."""
    return {k: {"models": v["models"], "display": v["display"], "key_name": v["key_name"]}
            for k, v in PROVIDERS.items()}
