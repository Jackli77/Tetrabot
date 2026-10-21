"""The agent runtime: the loop that turns a question into an answer.

A chatbot answers.  An agent *acts*: it decides which tool would answer the
question, runs it, reads the result, and only then writes the answer.  The
difference is visible — and that is exactly what this module makes
visible.

The loop is the classic **reason → act → observe** cycle:

1. the model is asked the question, with the tools it may call;
2. if it asks for a tool, the tool runs and its result is fed back;
3. the model sees the observation and decides again;
4. when it stops asking for tools, it writes the answer.

Three properties make it a *good* agent rather than a loop:

* **parallel tools.**  A model often wants the weather *and* the time at
  once: the tools run concurrently instead of one after the other.
* **a per-run cache.**  The same lookup twice in one run is computed
  once, so a confused model cannot hammer a public API.
* **a trace.**  Every step is recorded, with its duration, so the run can
  be shown, explained and measured.  :class:`AgentTrace` is that record.

The module is pure: it knows about tools and models, never about Discord.
The transport (a channel, a terminal) is the caller's business.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from tetrabot import config
from tetrabot.models import llm
from tetrabot.models.tools import registry
from tetrabot.models.tools.base import Tool

logger = logging.getLogger(__name__)

#: The kinds of step a trace holds.
KIND_THINK = "think"
KIND_TOOL = "tool"
KIND_OBSERVATION = "observation"
KIND_ANSWER = "answer"

#: How much of a step is kept in the trace, in characters.
TRACE_CONTENT_LIMIT = 600

#: The message sent to the model when the tool budget is exhausted.
BUDGET_EXHAUSTED = (
    "You have used all your tool calls. Answer the question now, using only "
    "the information you already gathered. If the information is not enough, "
    "say so plainly instead of guessing."
)


@dataclass
class AgentStep:
    """One step of a run: what the agent did, and how long it took."""

    kind: str
    name: str = ""
    content: str = ""
    duration_ms: int = 0
    ok: bool = True

    def render(self) -> str:
        """The step as a single line, for a terminal or a log."""
        icon = {
            KIND_THINK: "think",
            KIND_TOOL: "tool",
            KIND_OBSERVATION: "observe",
            KIND_ANSWER: "answer",
        }.get(self.kind, self.kind)
        label = f"{icon}:{self.name}" if self.name else icon
        return f"[{self.duration_ms:>5}ms] {label} — {self.content}"


@dataclass
class AgentTrace:
    """The record of a whole run — the agent's visible reasoning.

    It is the difference between "the bot said something" and "here is
    what the bot did to find out".  A trace can be rendered for a human
    (a terminal, a Discord embed) or inspected by a test.
    """

    steps: list[AgentStep] = field(default_factory=list)
    answer: str = ""
    rounds: int = 0
    duration_ms: int = 0
    tool_calls: int = 0
    tools_used: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        """Whether the run produced an answer without failing."""
        return not self.error and bool(self.answer.strip())

    @property
    def tool_names(self) -> list[str]:
        """The names of the tools the agent called, in order."""
        return list(self.tools_used)

    def add(
        self,
        kind: str,
        name: str = "",
        content: str = "",
        duration_ms: int = 0,
        ok: bool = True,
    ) -> AgentStep:
        """Record a step of the run and return it."""
        step = AgentStep(
            kind=kind,
            name=name,
            content=content[:TRACE_CONTENT_LIMIT],
            duration_ms=duration_ms,
            ok=ok,
        )
        self.steps.append(step)
        return step

    def summary(self) -> str:
        """A one-line summary of the run, for a log or a footer."""
        return (
            f"{self.rounds} round(s) · {self.tool_calls} tool call(s) "
            f"· {self.duration_ms}ms"
        )

    def render(self) -> str:
        """The whole trace as text, one step per line."""
        lines = [f"── trace ({self.summary()}) ──"]
        lines.extend(step.render() for step in self.steps)
        if self.answer:
            lines.append(f"answer: {self.answer}")
        if self.error:
            lines.append(f"error: {self.error}")
        return "\n".join(lines)


class AgentBackend(Protocol):
    """What the agent needs from a model.

    Keeping this a tiny protocol is what lets the agent run against the
    real Ollama server, against a scripted model (for the demo and the
    tests), or against anything else, without changing a line of the loop.
    """

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> llm.Completion:
        """Answer the conversation, possibly asking for tools."""
        ...

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[str | llm.ToolCall]:
        """Answer the conversation, yielding the text as it is produced."""
        ...


@dataclass
class OllamaBackend:
    """The real backend: the local Ollama server."""

    system: str = ""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> llm.Completion:
        """Ask the model once and get the whole answer."""
        return await llm.complete(
            messages=messages,
            tools=tools,
            system=self.system or None,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[str | llm.ToolCall]:
        """Ask the model, yielding the text as it is produced."""
        async for item in llm.stream_complete(
            messages=messages,
            tools=tools,
            system=self.system or None,
        ):
            yield item


class Agent:
    """The reason → act → observe loop, with a trace of everything it does.

    ``run()`` is the whole interface: give it a question, get back a trace
    holding the answer.  The caller decides how to show the answer; the
    agent does not know about channels, terminals or embeds.
    """

    def __init__(
        self,
        backend: AgentBackend | None = None,
        *,
        tools: list[Tool] | None = None,
        system: str = "",
        max_rounds: int | None = None,
    ):
        self.backend = backend or OllamaBackend(system=system)
        #: The system prompt framing the agent's role.
        self.system = system
        self.tools = tools if tools is not None else registry.enabled_tools()
        self.max_rounds = (
            max_rounds if max_rounds is not None else config.CHAT_MAX_TOOL_ROUNDS
        )

    @property
    def schemas(self) -> list[dict[str, Any]]:
        """The tools the model is allowed to call."""
        return [tool.schema() for tool in self.tools]

    def _find_tool(self, name: str) -> Tool | None:
        """The tool of that name, if the agent has it."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    async def _run_tools(
        self,
        calls: list[llm.ToolCall],
        trace: AgentTrace,
        cache: dict[str, str],
    ) -> list[str]:
        """Run the tools the model asked for, and return their results.

        The tools run **in parallel**: a model that wants the weather and
        the time at once should not wait for them one after the other.
        A tool that was already run in this same round is not run again —
        its result comes from the cache.
        """

        async def run_one(call: llm.ToolCall) -> tuple[str, bool, int]:
            key = _cache_key(call)
            if key in cache:
                return cache[key], True, 0

            started = time.monotonic()
            tool = self._find_tool(call.name)
            if tool is None:
                elapsed = int((time.monotonic() - started) * 1000)
                return (
                    json.dumps(
                        {"ok": False, "error": f"there is no tool called {call.name!r}"},
                        ensure_ascii=False,
                    ),
                    False,
                    elapsed,
                )

            logger.info("agent calls the tool %s(%s)", call.name, call.arguments)
            result = await tool.call(**call.arguments)
            elapsed = int((time.monotonic() - started) * 1000)
            text = result.to_text()
            # Remember the result: the same lookup twice in one run is
            # computed once, so a confused model cannot hammer a public API.
            cache[key] = text
            return text, result.ok, elapsed

        results = await asyncio.gather(*(run_one(call) for call in calls))

        for call, (text, ok, elapsed) in zip(calls, results, strict=True):
            trace.add(
                KIND_TOOL,
                name=call.name,
                content=json.dumps(call.arguments, ensure_ascii=False),
                duration_ms=elapsed,
                ok=ok,
            )
            trace.add(
                KIND_OBSERVATION,
                name=call.name,
                content=text,
                duration_ms=elapsed,
                ok=ok,
            )
            trace.tool_calls += 1
            if call.name not in trace.tools_used:
                trace.tools_used.append(call.name)

        return [text for text, _, _ in results]

    async def run(
        self,
        question: str,
        context: list[str] | None = None,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentTrace:
        """Answer a question, and record everything that was done.

        The trace holds the answer, the tools that were called, their
        results and how long each step took.  A failure of the model is
        recorded in the trace too, so the caller can report it.

        ``on_delta`` is called with the text as it is produced, so a
        caller can show the answer while it is being written.  It is
        optional: without it the answer is produced in one go.
        """
        trace = AgentTrace()
        started = time.monotonic()
        messages = llm.build_conversation(question, context or [], self.system)
        cache: dict[str, str] = {}

        for _round in range(self.max_rounds):
            trace.rounds += 1
            text, calls = await self._ask(messages, on_delta)

            if not calls:
                trace.add(KIND_ANSWER, content=text)
                trace.answer = text.strip()
                if not trace.answer:
                    # A thinking model can burn its whole budget on reasoning
                    # and return nothing.  That is a failure of the model,
                    # not an empty answer: the caller can retry with more.
                    raise llm.OllamaEmpty("Ollama returned an empty answer")
                break

            # The model wants tools: run them, feed the results back, and
            # let it write the real answer in the next round.
            if text.strip():
                trace.add(KIND_THINK, content=text.strip())

            messages.append(llm.tool_call_message(calls, text))
            results = await self._run_tools(calls, trace, cache)
            for call, result in zip(calls, results, strict=True):
                messages.append(call.as_result(result))
        else:
            # The budget is exhausted: ask for the best answer possible
            # with what was gathered, rather than staying silent.  No tool
            # is offered here, so the model has to answer.
            messages.append({"role": "user", "content": BUDGET_EXHAUSTED})
            text, _ = await self._ask(messages, on_delta, tools=[])
            trace.rounds += 1
            trace.add(KIND_ANSWER, content=text)
            trace.answer = text.strip()
            if not trace.answer:
                raise llm.OllamaEmpty("Ollama returned an empty answer")

        trace.duration_ms = int((time.monotonic() - started) * 1000)
        return trace

    async def _ask(
        self,
        messages: list[dict[str, Any]],
        on_delta: Callable[[str], Awaitable[None]] | None,
        tools: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[llm.ToolCall]]:
        """Ask the model once, and collect its text and its tool calls.

        With an ``on_delta`` callback the answer is streamed, so the caller
        can show it as it is written; without it the model is asked in one
        go, which is cheaper.
        """
        schemas = self.schemas if tools is None else tools

        if on_delta is None:
            completion = await self.backend.complete(messages, schemas)
            return completion.content, completion.tool_calls

        text = ""
        calls: list[llm.ToolCall] = []
        async for item in self.backend.stream(messages, schemas):
            if isinstance(item, llm.ToolCall):
                calls.append(item)
                continue
            text += item
            await on_delta(text)
        return text, calls


def _cache_key(call: llm.ToolCall) -> str:
    """The key a tool call is cached under.

    Two calls with the same name and the same arguments are the same
    lookup, so the second one is free.
    """
    arguments = json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)
    return f"{call.name}:{arguments}"


__all__ = [
    "BUDGET_EXHAUSTED",
    "KIND_ANSWER",
    "KIND_OBSERVATION",
    "KIND_THINK",
    "KIND_TOOL",
    "TRACE_CONTENT_LIMIT",
    "Agent",
    "AgentBackend",
    "AgentStep",
    "AgentTrace",
    "OllamaBackend",
]
