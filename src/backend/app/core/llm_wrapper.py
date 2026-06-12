# src/backend/app/core/llm_wrapper.py
"""Multi-provider completion wrapper, ported from the original app/core/llm_wrapper.py.

One get_llm_completion() that routes by model-name prefix (gpt- / claude- / gemini-).
Swapping providers is a config change — that is how the original's fix-4 model swap
shipped in hours.

Deviation (documented): the original called sys.exit(1) on client-init failure; here we
log critical and return None so a misconfigured provider degrades instead of killing the
worker. Any other failure also returns None — retries belong to the callers.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .config import settings

logger = logging.getLogger(__name__)

_openai_client: Any = None
_anthropic_client: Any = None
_google_client: Any = None


def _initialize_openai() -> Any:
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _initialize_anthropic() -> Any:
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def _initialize_google() -> Any:
    global _google_client
    if _google_client is None:
        from google import genai
        _google_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    return _google_client


def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    return system, rest


def get_llm_completion(model_name: str, messages: list[dict], temperature: float = 0.2,
                       max_tokens: int = 10000,
                       response_format: Optional[dict] = None) -> Optional[str]:
    """Return the completion text, or None on any failure (callers own the retries)."""
    try:
        if model_name.startswith("gpt-"):
            client = _initialize_openai()
            kwargs: dict[str, Any] = {}
            if response_format:
                kwargs["response_format"] = response_format
            resp = client.chat.completions.create(
                model=model_name, messages=messages, temperature=temperature,
                max_tokens=max_tokens, **kwargs)
            return resp.choices[0].message.content

        if model_name.startswith("claude-"):
            client = _initialize_anthropic()
            system, rest = _split_system(messages)
            resp = client.messages.create(
                model=model_name, system=system or None, messages=rest,
                temperature=temperature, max_tokens=max_tokens)
            return resp.content[0].text

        if model_name.startswith("gemini-"):
            from google.genai import types
            client = _initialize_google()
            system, rest = _split_system(messages)
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system or None,
                response_mime_type=("application/json"
                                    if response_format
                                    and response_format.get("type") == "json_object"
                                    else None),
            )
            contents = "\n\n".join(m["content"] for m in rest)
            resp = client.models.generate_content(
                model=model_name, contents=contents, config=config)
            return resp.text

        logger.error("Unknown model prefix for '%s' - no provider route", model_name)
        return None
    except Exception:
        logger.exception("get_llm_completion failed for model '%s'", model_name)
        return None
