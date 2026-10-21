"""Tests for the tool-calling loop of the agent.

The model asks for a tool, the agent runs it, feeds the result back, and
the model writes the final answer.  These tests drive the loop with a
scripted model, so no network and no real model are needed.
"""
from __future__ import annotations

import asyncio

from tetrabot.models.agent import Agent
from tetrabot.models.tools.stubs import stub_tools

from .conftest import FakeModel


def build_agent(script, max_rounds=3):
    """An agent with a scripted model and the stub tools."""
    model = FakeModel(script)
    agent = Agent(
        backend=model,
        tools=stub_tools(),
        max_rounds=max_rounds,
    )
    return agent, model


class TestToolLoop:
    def test_a_tool_is_run_and_its_result_is_fed_back(self):
        """The model asks for the weather, the tool runs, the model answers."""
        agent, model = build_agent(
            [
                ("", [("get_weather", {"city": "Paris"})]),
                ("Il fait 14 degres a Paris.", []),
            ]
        )
        trace = asyncio.run(agent.run("Quel temps fait-il a Paris ?"))

        assert len(model.rounds) == 2, "the model should be asked twice"
        # The second round carries the tool result.
        assert model.rounds[1][-1]["role"] == "tool"
        assert "14" in model.rounds[1][-1]["content"]
        assert trace.answer == "Il fait 14 degres a Paris."

    def test_several_tools_at_once_are_all_run(self):
        """The model may ask for two tools in the same turn."""
        agent, model = build_agent(
            [
                (
                    "",
                    [
                        ("get_weather", {"city": "Paris"}),
                        ("get_datetime", {"timezone": "Europe/Paris"}),
                    ],
                ),
                ("Voici.", []),
            ]
        )
        asyncio.run(agent.run("Meteo et heure ?"))

        # Both results are fed back, one tool message each.
        tool_messages = [m for m in model.rounds[1] if m["role"] == "tool"]
        assert len(tool_messages) == 2

    def test_the_tool_call_message_has_the_right_shape(self):
        """The assistant message must hold every call of the turn."""
        agent, model = build_agent(
            [
                (
                    "",
                    [
                        ("get_weather", {"city": "Paris"}),
                        ("get_datetime", {"timezone": "Europe/Paris"}),
                    ],
                ),
                ("ok", []),
            ]
        )
        asyncio.run(agent.run("question"))

        assistant = [m for m in model.rounds[1] if m["role"] == "assistant"]
        assert len(assistant) == 1
        calls = assistant[0]["tool_calls"]
        assert len(calls) == 2
        # The id belongs to the call, not to the function: Ollama answers
        # with a 500 when it is nested one level too deep.
        assert calls[0]["id"] == "c0"
        assert calls[0]["function"]["name"] == "get_weather"

    def test_an_unknown_tool_is_reported_to_the_model(self):
        """A tool that does not exist produces a message, not a crash."""
        agent, model = build_agent(
            [
                ("", [("nope", {})]),
                ("Je ne peux pas faire cela.", []),
            ]
        )
        trace = asyncio.run(agent.run("question"))

        # The model is told the tool does not exist.
        assert "nope" in model.rounds[1][-1]["content"]
        assert trace.ok is True

    def test_the_loop_stops_after_the_maximum_rounds(self):
        """A model that keeps asking for tools is stopped."""
        agent, model = build_agent(
            [
                ("", [("get_weather", {"city": "Paris"})]),
                ("", [("get_weather", {"city": "Paris"})]),
                ("Voici ce que j'ai.", []),
            ],
            max_rounds=2,
        )
        trace = asyncio.run(agent.run("boucle"))

        # The budget is bounded: two tool rounds, then the final answer.
        assert len(model.rounds) == 3
        assert trace.answer == "Voici ce que j'ai."
        # The final answer is asked without tools: the model must answer.
        assert model.offered[-1] == []

    def test_the_tool_schemas_are_offered_to_the_model(self):
        agent, model = build_agent([("ok", [])])
        asyncio.run(agent.run("salut"))

        names = {t["function"]["name"] for t in model.offered[0]}
        assert "get_weather" in names
        assert "search_wikipedia" in names
