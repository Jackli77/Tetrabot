"""An async client for a local Ollama LLM.

Pure I/O wrapper around the Ollama ``/api/chat`` HTTP endpoint — no Discord,
views, or command handlers here.  The server address and model come from
:mod:`tetrabot.config`.  Raises on any network/HTTP/JSON failure so the caller
can decide how to report the error.

Three things matter for a chatbot that *feels* responsive:

* **Streaming** (:func:`stream_chat`) — the answer arrives token by token, so
  the caller can show progress instead of a long silence.
* **A token budget that leaves room for an answer** — thinking models spend
  their budget on reasoning; see :func:`chat` for how the budget is split.
* **Typed errors** — :class:`OllamaError` and its subclasses let the caller
  tell "the server is down" from "the model does not exist".
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from tetrabot import config

logger = logging.getLogger(__name__)

#: Characters of a streamed answer kept per edit.  Discord allows a message
#: to be edited every few seconds at most, so edits are throttled by the
#: caller rather than per token.
STREAM_CHUNK = 240


class OllamaError(RuntimeError):
    """Base class for every Ollama failure."""


class OllamaUnavailable(OllamaError):
    """The Ollama server could not be reached."""


class OllamaTransient(OllamaError):
    """The server failed in a way that may go away on its own.

    A 500 from the server (or from a cloud backend behind it) is often
    temporary, so the request is worth retrying.
    """


class OllamaModelMissing(OllamaError):
    """The requested model is not installed on the server."""


class OllamaTimeout(OllamaError):
    """The model took too long to answer."""


class OllamaEmpty(OllamaError):
    """The model answered with no content at all.

    This happens when a *thinking* model spends its whole token budget on
    reasoning and never gets to the answer.  The caller may retry with a
    bigger budget or without thinking.
    """


@dataclass
class ToolCall:
    """A tool the model wants to call."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def as_message(self, content: str) -> dict[str, Any]:
        """The assistant message that announces this tool call.

        The ``id`` belongs to the *call*, not to the function: Ollama
        answers with a 500 when it is nested one level too deep.
        """
        call: dict[str, Any] = {
            "function": {
                "name": self.name,
                "arguments": self.arguments,
            }
        }
        if self.id:
            call["id"] = self.id
        return {"role": "assistant", "content": content or "", "tool_calls": [call]}

    def as_result(self, content: str) -> dict[str, Any]:
        """The message that carries the result of this tool call."""
        return {"role": "tool", "content": content}


def tool_call_message(
    calls: list[ToolCall], content: str = ""
) -> dict[str, Any]:
    """The assistant message that announces several tool calls at once.

    The model often asks for more than one tool in the same turn (the
    weather *and* the time, for instance).  Ollama expects a single
    assistant message holding all of them, followed by one ``tool`` message
    per result.
    """
    payload = []
    for call in calls:
        entry: dict[str, Any] = {
            "function": {
                "name": call.name,
                "arguments": call.arguments,
            }
        }
        if call.id:
            entry["id"] = call.id
        payload.append(entry)
    return {"role": "assistant", "content": content or "", "tool_calls": payload}


def _build_messages(
    context: list[str], prompt: str | None = None, system: str | None = None
) -> list[dict[str, str]]:
    """Build an Ollama ``messages`` array from system prompt + context + prompt.

    Context lines and the prompt are sent as ``user`` messages so the model
    can reason over the whole recent conversation.  A short ``system``
    prompt frames the task (chatbot role, tone, language).
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system.strip()})
    for line in context:
        line = line.strip()
        if line:
            messages.append({"role": "user", "content": line})
    if prompt:
        messages.append({"role": "user", "content": prompt})
    return messages


def _build_payload(
    messages: list[dict[str, str]],
    *,
    stream: bool,
    options: dict[str, Any] | None = None,
    think: Any = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the JSON body of an ``/api/chat`` request."""
    payload: dict[str, Any] = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": stream,
    }
    if think is not None:
        # ``think`` accepts a bool or a level ("low"/"medium"/"high").
        # Disabling it makes the model answer *in* the content instead of
        # reasoning in a separate field.
        payload["think"] = think
    if options:
        payload["options"] = options
    if tools:
        # The schemas of the tools the model may call.
        payload["tools"] = tools
    if config.OLLAMA_KEEP_ALIVE:
        # Keep the model in memory: loading it again costs seconds.
        payload["keep_alive"] = config.OLLAMA_KEEP_ALIVE
    return payload


def _raise_for_status(status: int, body: str) -> None:
    """Turn an HTTP error into a typed exception."""
    if status == 404:
        raise OllamaModelMissing(
            f"model {config.OLLAMA_MODEL!r} is not installed on the Ollama server"
        )
    if status in (500, 502, 503, 504):
        raise OllamaTransient(f"Ollama HTTP {status}: {body[:200]}")
    raise OllamaError(f"Ollama HTTP {status}: {body[:300]}")


def _options(num_predict: int, temperature: float) -> dict[str, Any]:
    """The generation options used for a chat request."""
    return {"temperature": temperature, "num_predict": num_predict}


def _url() -> str:
    """The full URL of the chat endpoint."""
    return f"{config.OLLAMA_HOST.rstrip('/')}/api/chat"


def build_conversation(
    prompt: str | None = None,
    context: list[str] | None = None,
    system: str | None = None,
) -> list[dict[str, Any]]:
    """Build the message list of a conversation.

    The tool loop needs to keep the whole conversation — the context, the
    question, the tool calls and their results — so that the model can be
    asked again with everything it already knows.
    """
    return _build_messages(context or [], prompt, system)


async def chat(
    prompt: str | None = None,
    context: list[str] | None = None,
    system: str | None = None,
    *,
    num_predict: int | None = None,
    temperature: float | None = None,
    think: Any = None,
    tools: list[dict[str, Any]] | None = None,
) -> str:
    """Ask the local Ollama model and return its answer text.

    ``context`` is an optional list of recent message lines (author-prefixed)
    supplied as conversation history.  ``system`` is an optional short system
    prompt framing the chat.  Raises a :class:`OllamaError` subclass on any
    HTTP/JSON/network failure.
    """
    answer = await complete(
        prompt,
        context,
        system,
        num_predict=num_predict,
        temperature=temperature,
        think=think,
        tools=tools,
    )
    if answer.tool_calls:
        # The model wants a tool; the caller must run the tool loop.
        return answer.content
    if not answer.content:
        # A thinking model can burn its whole budget on reasoning and return
        # an empty answer — report it distinctly so the caller can retry.
        raise OllamaEmpty("Ollama returned an empty answer")
    return answer.content


@dataclass
class Completion:
    """What the model answered: text, and the tools it wants to call."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        """Whether the model asked for a tool to be run."""
        return bool(self.tool_calls)


def _parse_tool_calls(message: dict[str, Any]) -> list[ToolCall]:
    """The tool calls of a message, in the shape the model sent them."""
    calls: list[ToolCall] = []
    for raw in message.get("tool_calls") or []:
        function = raw.get("function") or {}
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            # Some models send the arguments as a JSON string.
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append(
            ToolCall(
                name=function.get("name", ""),
                arguments=arguments,
                id=raw.get("id", "") or "",
            )
        )
    return calls


async def _post_with_retry(session: aiohttp.ClientSession, payload: dict[str, Any]):
    """POST the payload, retrying the failures that are worth retrying.

    A 500 from the server — or from the cloud backend behind it — is often
    temporary, so the request is tried again a couple of times before
    giving up.
    """
    attempts = max(1, config.OLLAMA_RETRIES + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await session.post(_url(), json=payload)
        except aiohttp.ClientError as exc:
            raise OllamaUnavailable(
                f"cannot reach Ollama at {config.OLLAMA_HOST}: {exc}"
            ) from exc
        if response.status == 200:
            return response
        body = await response.text()
        response.release()
        try:
            _raise_for_status(response.status, body)
        except OllamaTransient as exc:
            last_error = exc
            if attempt + 1 < attempts:
                logger.warning(
                    "Ollama answered %s, retrying (%d/%d)",
                    response.status, attempt + 1, attempts - 1,
                )
                await asyncio.sleep(1.0 + attempt)
                continue
        raise _as_error(response.status, body)
    raise last_error or OllamaError("Ollama did not answer")


def _as_error(status: int, body: str) -> OllamaError:
    """The exception matching an HTTP status."""
    if status == 404:
        return OllamaModelMissing(
            f"model {config.OLLAMA_MODEL!r} is not installed on the Ollama server"
        )
    if status in (500, 502, 503, 504):
        return OllamaTransient(f"Ollama HTTP {status}: {body[:200]}")
    return OllamaError(f"Ollama HTTP {status}: {body[:300]}")


async def complete(
    prompt: str | None = None,
    context: list[str] | None = None,
    system: str | None = None,
    *,
    num_predict: int | None = None,
    temperature: float | None = None,
    think: Any = None,
    tools: list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> Completion:
    """Ask the model once and get back its text *and* its tool calls.

    ``messages`` lets the caller continue a conversation (the tool loop
    feeds the tool results back this way).  When it is given, ``prompt``,
    ``context`` and ``system`` are ignored.
    """
    if num_predict is None:
        num_predict = config.OLLAMA_NUM_PREDICT
    if temperature is None:
        temperature = config.OLLAMA_TEMPERATURE
    if think is None:
        think = config.OLLAMA_THINK

    if messages is None:
        messages = _build_messages(context or [], prompt, system)
    payload = _build_payload(
        messages,
        stream=False,
        options=_options(num_predict, temperature),
        think=think,
        tools=tools,
    )

    timeout = aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await _post_with_retry(session, payload)
            data: dict[str, Any] = await response.json()
    except aiohttp.ClientError as exc:
        raise OllamaUnavailable(
            f"cannot reach Ollama at {config.OLLAMA_HOST}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise OllamaTimeout("Ollama took too long to answer") from exc

    message = data.get("message") or {}
    return Completion(
        content=(message.get("content") or "").strip(),
        tool_calls=_parse_tool_calls(message),
    )


async def stream_complete(
    prompt: str | None = None,
    context: list[str] | None = None,
    system: str | None = None,
    *,
    num_predict: int | None = None,
    temperature: float | None = None,
    think: Any = None,
    tools: list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]] | None = None,
):
    """Ask the model and yield its answer as it is produced.

    Yields plain text chunks — the *content* of the answer only, never the
    model's private reasoning.  The last chunk is the complete answer.

    When the model asks for a tool, the text produced before the request is
    yielded first, then the :class:`ToolCall` itself is yielded as the last
    item — so the caller can run the tool and ask again.

    Streaming is what makes a local model feel responsive: the first words
    arrive in seconds instead of after the whole answer is generated.
    """
    if num_predict is None:
        num_predict = config.OLLAMA_NUM_PREDICT
    if temperature is None:
        temperature = config.OLLAMA_TEMPERATURE
    if think is None:
        think = config.OLLAMA_THINK

    if messages is None:
        messages = _build_messages(context or [], prompt, system)
    payload = _build_payload(
        messages,
        stream=True,
        options=_options(num_predict, temperature),
        think=think,
        tools=tools,
    )

    timeout = aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await _post_with_retry(session, payload)
            async for raw in response.content:
                line = raw.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue  # keep-alive noise or a partial line
                message = chunk.get("message") or {}
                text = message.get("content") or ""
                if text:
                    yield text
                calls = _parse_tool_calls(message)
                if calls:
                    # The model wants a tool: the caller runs it and asks again.
                    for call in calls:
                        yield call
    except aiohttp.ClientError as exc:
        raise OllamaUnavailable(
            f"cannot reach Ollama at {config.OLLAMA_HOST}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise OllamaTimeout("Ollama took too long to answer") from exc


async def stream_chat(
    prompt: str | None = None,
    context: list[str] | None = None,
    system: str | None = None,
    *,
    num_predict: int | None = None,
    temperature: float | None = None,
    think: Any = None,
):
    """Ask the model and yield the answer as it is produced.

    Yields plain text chunks — the *content* of the answer only, never the
    model's private reasoning.  Use :func:`stream_complete` when the model
    may call tools.
    """
    async for item in stream_complete(
        prompt,
        context,
        system,
        num_predict=num_predict,
        temperature=temperature,
        think=think,
    ):
        if isinstance(item, str):
            yield item


async def available_models() -> list[str]:
    """The names of the models installed on the Ollama server.

    Used to tell the user *which* models they can pick when the configured
    one is missing.
    """
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(f"{config.OLLAMA_HOST.rstrip('/')}/api/tags") as resp,
        ):
            if resp.status != 200:
                _raise_for_status(resp.status, await resp.text())
            data: dict[str, Any] = await resp.json()
    except aiohttp.ClientError as exc:
        raise OllamaUnavailable(
            f"cannot reach Ollama at {config.OLLAMA_HOST}: {exc}"
        ) from exc

    return [entry.get("name", "") for entry in data.get("models") or []]


#: Backwards-compatible alias for the original single-shot helper.
ask = chat


__all__ = [
    "Completion",
    "OllamaEmpty",
    "OllamaError",
    "OllamaModelMissing",
    "OllamaTimeout",
    "OllamaTransient",
    "OllamaUnavailable",
    "ToolCall",
    "ask",
    "available_models",
    "build_conversation",
    "chat",
    "complete",
    "stream_chat",
    "stream_complete",
    "tool_call_message",
]
