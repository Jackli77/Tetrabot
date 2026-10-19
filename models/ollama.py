"""MODEL layer: async client for a local Ollama LLM.

Pure I/O wrapper around the Ollama ``/api/chat`` HTTP endpoint — no Discord,
views, or controllers here.  The server address and model come from
:mod:`config.settings`.  Raises on any network/HTTP/JSON failure so the caller
can decide how to report the error.
"""
from __future__ import annotations

from typing import Any

import aiohttp

from config import settings


def _build_messages(context: list[str], prompt: str) -> list[dict[str, str]]:
    """Build an Ollama ``messages`` array from recent context + the new prompt.

    Context lines and the prompt are all sent as ``user`` messages so the model
    can reason over the whole recent conversation.
    """
    messages: list[dict[str, str]] = []
    for line in context:
        line = line.strip()
        if line:
            messages.append({"role": "user", "content": line})
    messages.append({"role": "user", "content": prompt})
    return messages


async def ask_ollama(prompt: str, context: list[str] | None = None) -> str:
    """Ask the local Ollama model and return its answer text.

    ``context`` is an optional list of recent message lines (author-prefixed)
    supplied as conversation history.  Raises on any HTTP/JSON/network failure.
    """
    url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": _build_messages(context or [], prompt),
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512},
    }

    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Ollama HTTP {resp.status}: {text[:300]}")
            data: dict[str, Any] = await resp.json()

    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Ollama returned an empty answer")
    return content.strip()


__all__ = ["ask_ollama"]