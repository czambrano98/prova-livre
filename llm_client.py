"""
LLM client for the exam-builder app.

- Loads .env from the repo folder first, then one folder above (per course rules).
- Calls gpt-6-luna through the Portkey gateway using the OpenAI-compatible API.
- Records token usage for the tokenomics report.

Environment variables (see .env.example):
    PORTKEY_API_KEY   required (course key)
    OPENAI_API_KEY    optional (only if running your own paid model)
    LLM_MODEL         optional override of the model name (default: gpt-6-luna)
    LLM_BASE_URL      optional override of the base URL
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from tools.token_logger import log_usage

# --------------------------------------------------------------------------- #
# .env loading: repo folder first, then one level up (course requirement).
# --------------------------------------------------------------------------- #
_REPO_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _REPO_DIR.parent

# Load repo .env first so it takes precedence; then fill any gaps from parent.
load_dotenv(_REPO_DIR / ".env", override=False)
load_dotenv(_PARENT_DIR / ".env", override=False)

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gpt-6-luna")
PORTKEY_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.portkey.ai/v1")


class LLMConfigError(RuntimeError):
    """Raised when no usable API key is configured."""


@dataclass
class ChatResult:
    text: str
    model: str
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw: Any = field(default=None, repr=False)


def _build_client() -> tuple[str, Any, str]:
    """Return (provider, client, model).

    Priority: course Portkey key (gpt-6-luna) -> your own OpenAI key -> your own
    Anthropic/Claude key. The first key found wins, so graders with PORTKEY_API_KEY
    always hit the course model.
    """
    portkey_key = os.environ.get("PORTKEY_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    override = os.environ.get("LLM_MODEL", "").strip()

    if portkey_key:
        client = OpenAI(api_key=portkey_key, base_url=PORTKEY_BASE_URL)
        return "openai", client, (override or DEFAULT_MODEL)
    if openai_key:
        client = OpenAI(api_key=openai_key)
        return "openai", client, (override or "gpt-4o-mini")
    if anthropic_key:
        import anthropic  # imported only when a Claude key is actually used

        client = anthropic.Anthropic(api_key=anthropic_key)
        return "anthropic", client, (override or "claude-opus-5-5")

    raise LLMConfigError(
        "No API key found. Put PORTKEY_API_KEY (course), OPENAI_API_KEY, or "
        "ANTHROPIC_API_KEY in a .env file in this folder or one folder above it. "
        "See .env.example."
    )


# Some gpt-6-luna deployments (Azure-routed reasoning models) reject custom
# temperature and require max_completion_tokens instead of max_tokens. We learn
# that on the first call and stop sending the offending params.
_SUPPORTS_TEMPERATURE = True


def _create_with_fallback(client: OpenAI, kwargs: dict[str, Any]):
    """Call the API, stripping params the model rejects (temperature, token field)."""
    global _SUPPORTS_TEMPERATURE
    from openai import BadRequestError

    # token limit param: this model family uses max_completion_tokens
    if "max_tokens" in kwargs:
        kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
    if not _SUPPORTS_TEMPERATURE:
        kwargs.pop("temperature", None)

    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as err:
        msg = str(err).lower()
        changed = False
        if "temperature" in msg and "temperature" in kwargs:
            kwargs.pop("temperature", None)
            _SUPPORTS_TEMPERATURE = False
            changed = True
        if "max_completion_tokens" in msg and "max_completion_tokens" in kwargs:
            # Fall back to no explicit cap if even this is rejected.
            kwargs.pop("max_completion_tokens", None)
            changed = True
        if "max_tokens" in msg and "max_completion_tokens" in kwargs:
            changed = True  # already renamed; retry
        if not changed:
            raise
        return client.chat.completions.create(**kwargs)


def _anthropic_chat(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None,
    label: str,
) -> ChatResult:
    """Claude (Anthropic) path. Converts OpenAI-style messages to the Messages API.

    The system role is a separate parameter; temperature is not sent (rejected by
    current Claude models). max_tokens is required, so we default it generously.
    """
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    convo = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens or 16000,
        "messages": convo,
    }
    if system_parts:
        kwargs["system"] = "\n\n".join(system_parts)

    resp = client.messages.create(**kwargs)

    text = "".join(
        getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text"
    )
    usage = getattr(resp, "usage", None)
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    cached_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    # Match OpenAI semantics: prompt_tokens includes the cached portion.
    prompt_tokens = input_tokens + cached_tokens
    total_tokens = prompt_tokens + completion_tokens

    log_usage(
        label=label,
        model=model,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    return ChatResult(
        text=text,
        model=model,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        raw=resp,
    )


def chat(
    messages: list[dict[str, str]],
    *,
    label: str = "llm",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    model: str | None = None,
) -> ChatResult:
    """Single chat completion. Records token usage under `label`."""
    provider, client, resolved_model = _build_client()
    resolved_model = model or resolved_model

    if provider == "anthropic":
        return _anthropic_chat(
            client, resolved_model, messages, max_tokens=max_tokens, label=label
        )

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = _create_with_fallback(client, kwargs)

    usage = getattr(resp, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    cached_tokens = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached_tokens = getattr(details, "cached_tokens", 0) or 0

    text = resp.choices[0].message.content or ""

    log_usage(
        label=label,
        model=resolved_model,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    return ChatResult(
        text=text,
        model=resolved_model,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        raw=resp,
    )


def _extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model response."""
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} or [...] span.
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from model output:\n{text[:500]}")


def chat_json(
    messages: list[dict[str, str]],
    *,
    label: str = "llm-json",
    temperature: float = 0.4,
    max_tokens: int | None = None,
    model: str | None = None,
    retries: int = 2,
) -> tuple[Any, ChatResult]:
    """Chat completion that returns parsed JSON plus the raw ChatResult.

    Retries once or twice if the model returns unparseable JSON.
    """
    last_err: Exception | None = None
    convo = list(messages)
    for attempt in range(retries + 1):
        result = chat(
            convo,
            label=label,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        try:
            return _extract_json(result.text), result
        except ValueError as err:
            last_err = err
            convo = convo + [
                {"role": "assistant", "content": result.text},
                {
                    "role": "user",
                    "content": "That was not valid JSON. Reply with ONLY valid JSON, no prose, no code fences.",
                },
            ]
    raise ValueError(f"Model did not return valid JSON after {retries + 1} tries: {last_err}")


def health_check() -> str:
    """Tiny call to confirm the key + model work. Returns the model's reply."""
    result = chat(
        [{"role": "user", "content": "Reply with exactly: OK"}],
        label="health-check",
        temperature=0.0,
        max_tokens=1024,  # generous so thinking models (Claude) have room
    )
    return result.text.strip()
