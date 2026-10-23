"""A scripted model: the same agent, with no model at all.

The agent is the interesting part of this project, and it should be
*demonstrable* without a GPU, an API key or a network connection.  This
module provides a model that replays a fixed script, so the whole loop —
reason, act, observe, answer — can be shown, tested and measured
deterministically.

A script is a list of :class:`ScriptedTurn`.  Each turn is what the model
"answers" at that point of the conversation: some text, and optionally the
tools it wants to call.  The turns are consumed in order, and the last one
is repeated once the script is over.

>>> script = [
...     ScriptedTurn(text="Let me check.", tools=[("get_weather", {"city": "Paris"})]),
...     ScriptedTurn(text="It is 14 degrees in Paris."),
... ]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tetrabot.models import llm


@dataclass
class ScriptedTurn:
    """One answer of the scripted model.

    ``tools`` is a list of ``(name, arguments)`` pairs — the calls the
    model asks for at that point.
    """

    text: str = ""
    tools: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def to_completion(self) -> llm.Completion:
        """The turn as the completion the agent expects."""
        return llm.Completion(
            content=self.text,
            tool_calls=[
                llm.ToolCall(name=name, arguments=arguments, id=f"call-{index}")
                for index, (name, arguments) in enumerate(self.tools)
            ],
        )


class ScriptedBackend:
    """A model that replays a script instead of thinking.

    It is a real :class:`~tetrabot.models.agent.AgentBackend`: the agent
    cannot tell the difference, which is exactly the point — the loop is
    exercised for real, only the reasoning is canned.
    """

    def __init__(self, script: list[ScriptedTurn] | None = None):
        self.script = list(script or [])
        self.calls: list[list[dict[str, Any]]] = []

    def push(self, turn: ScriptedTurn) -> None:
        """Add a turn to the end of the script."""
        self.script.append(turn)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> llm.Completion:
        """Return the next turn of the script."""
        self.calls.append(list(messages))
        if not self.script:
            return llm.Completion(content="")
        turn = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return turn.to_completion()

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ):
        """Yield the next turn of the script, word by word."""
        completion = await self.complete(messages, tools)
        for word in completion.content.split(" "):
            if word:
                yield word + " "
        for call in completion.tool_calls:
            yield call


__all__ = ["ScriptedBackend", "ScriptedTurn"]
