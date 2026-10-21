"""Tests for the agent core — the loop, the trace and its guarantees.

The agent is the heart of the project, so it is tested on its own: the
loop, the tools it calls, the cache that protects the public APIs, and
the trace that makes its reasoning visible.
"""
from __future__ import annotations

import asyncio

import pytest

from tetrabot.models import llm
from tetrabot.models.agent import Agent, AgentTrace
from tetrabot.models.tools.base import Tool
from tetrabot.models.tools.stubs import stub_tools

from .conftest import FakeModel


def build_agent(script, tools=None, max_rounds=3):
    """An agent with a scripted model and the given tools."""
    model = FakeModel(script)
    agent = Agent(
        backend=model,
        tools=tools if tools is not None else stub_tools(),
        max_rounds=max_rounds,
    )
    return agent, model


class TestAgentLoop:
    def test_a_question_without_a_tool_is_answered_directly(self):
        agent, model = build_agent([("Bonjour !", [])])
        trace = asyncio.run(agent.run("salut"))

        assert trace.answer == "Bonjour !"
        assert trace.rounds == 1
        assert trace.tool_calls == 0
        assert len(model.rounds) == 1

    def test_the_answer_is_asked_in_the_conversation(self):
        agent, model = build_agent([("ok", [])])
        agent.system = "You are Tetrabot."
        asyncio.run(agent.run("salut", context=["alice: bonjour"]))

        messages = model.rounds[0]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are Tetrabot."
        assert messages[1]["content"] == "alice: bonjour"
        assert messages[-1]["content"] == "salut"

    def test_the_tools_are_offered_to_the_model(self):
        agent, model = build_agent([("ok", [])])
        asyncio.run(agent.run("salut"))

        names = {tool["function"]["name"] for tool in model.offered[0]}
        assert names == {"get_weather", "search_wikipedia", "search_web", "get_datetime"}

    def test_the_trace_records_every_step(self):
        agent, model = build_agent(
            [
                ("Je regarde.", [("get_weather", {"city": "Paris"})]),
                ("Il fait 14 degres.", []),
            ]
        )
        trace = asyncio.run(agent.run("meteo ?"))

        kinds = [step.kind for step in trace.steps]
        assert kinds == ["think", "tool", "observation", "answer"]
        assert trace.tools_used == ["get_weather"]
        assert trace.tool_calls == 1

    def test_the_trace_holds_the_arguments_and_the_result(self):
        agent, model = build_agent(
            [
                ("", [("get_weather", {"city": "Paris"})]),
                ("ok", []),
            ]
        )
        trace = asyncio.run(agent.run("meteo ?"))

        tool_step, observation = trace.steps[0], trace.steps[1]
        assert "Paris" in tool_step.content
        assert "14" in observation.content
        assert observation.ok is True

    def test_the_trace_summarises_the_run(self):
        agent, model = build_agent([("ok", [])])
        trace = asyncio.run(agent.run("salut"))

        assert "1 round" in trace.summary()
        assert "0 tool call" in trace.summary()
        assert "ok" in trace.render()


class TestAgentBudget:
    def test_the_budget_is_bounded(self):
        """A model that always asks for a tool cannot loop forever."""
        agent, model = build_agent(
            [("", [("get_weather", {"city": "Paris"})])],
            max_rounds=2,
        )
        with pytest.raises(llm.OllamaEmpty):
            asyncio.run(agent.run("boucle"))

        assert len(model.rounds) == 3

    def test_an_empty_answer_is_reported_as_a_failure(self):
        """An empty answer is a model failure the caller can retry."""
        agent, model = build_agent([("", [])])
        with pytest.raises(llm.OllamaEmpty):
            asyncio.run(agent.run("salut"))

    def test_the_final_answer_is_asked_without_tools(self):
        """When the budget is spent, the model must answer with what it has."""
        agent, model = build_agent(
            [
                ("", [("get_weather", {"city": "Paris"})]),
                ("", [("get_weather", {"city": "Paris"})]),
                ("Voici.", []),
            ],
            max_rounds=2,
        )
        trace = asyncio.run(agent.run("meteo ?"))

        assert model.offered[-1] == [], "the last round must offer no tool"
        assert trace.answer == "Voici."


class TestAgentTools:
    def test_several_tools_run_in_parallel(self):
        """Two tools asked at once do not wait for each other."""
        order: list[str] = []

        async def slow(city: str):
            order.append("slow-start")
            await asyncio.sleep(0.05)
            order.append("slow-end")
            return llm.ToolResult(data={"city": city})

        async def fast(timezone: str):
            order.append("fast")
            return llm.ToolResult(data={"timezone": timezone})

        tools = [
            Tool(name="slow", description="", handler=slow),
            Tool(name="fast", description="", handler=fast),
        ]
        agent, model = build_agent(
            [
                ("", [("slow", {"city": "Paris"}), ("fast", {"timezone": "UTC"})]),
                ("ok", []),
            ],
            tools=tools,
        )
        asyncio.run(agent.run("question"))

        # The fast tool finished before the slow one: they ran together.
        assert order.index("fast") < order.index("slow-end")

    def test_a_tool_is_not_run_twice_in_the_same_run(self):
        """The cache protects the public APIs from a confused model."""
        calls: list[str] = []

        async def counter(city: str):
            calls.append(city)
            return llm.ToolResult(data={"city": city})

        tools = [Tool(name="counter", description="", handler=counter)]
        agent, model = build_agent(
            [
                (
                    "",
                    [
                        ("counter", {"city": "Paris"}),
                        ("counter", {"city": "Paris"}),
                    ],
                ),
                ("ok", []),
            ],
            tools=tools,
        )
        asyncio.run(agent.run("question"))

        assert calls == ["Paris"], "the second call must come from the cache"

    def test_a_different_argument_is_a_different_lookup(self):
        calls: list[str] = []

        async def counter(city: str):
            calls.append(city)
            return llm.ToolResult(data={"city": city})

        tools = [Tool(name="counter", description="", handler=counter)]
        agent, model = build_agent(
            [
                (
                    "",
                    [
                        ("counter", {"city": "Paris"}),
                        ("counter", {"city": "Lyon"}),
                    ],
                ),
                ("ok", []),
            ],
            tools=tools,
        )
        asyncio.run(agent.run("question"))

        assert calls == ["Paris", "Lyon"]

    def test_a_failing_tool_does_not_break_the_run(self):
        """A tool that fails is reported to the model, not to the bot."""
        async def broken(city: str):
            raise RuntimeError("the service is down")

        tools = [Tool(name="broken", description="", handler=broken)]
        agent, model = build_agent(
            [
                ("", [("broken", {"city": "Paris"})]),
                ("Desole, je ne peux pas.", []),
            ],
            tools=tools,
        )
        trace = asyncio.run(agent.run("question"))

        assert trace.answer == "Desole, je ne peux pas."
        assert trace.steps[1].ok is False


class TestAgentStreaming:
    def test_the_answer_is_produced_as_it_arrives(self):
        """``on_delta`` receives the text while it is written."""
        agent, model = build_agent([("bonjour le monde", [])])
        seen: list[str] = []

        async def on_delta(text: str) -> None:
            seen.append(text)

        asyncio.run(agent.run("salut", on_delta=on_delta))

        assert seen, "the callback must have been called"
        assert seen[-1].strip() == "bonjour le monde"

    def test_the_answer_is_produced_in_one_go_without_a_callback(self):
        agent, model = build_agent([("bonjour", [])])
        trace = asyncio.run(agent.run("salut"))

        assert trace.answer == "bonjour"


class TestAgentTrace:
    def test_an_empty_trace_says_so(self):
        trace = AgentTrace()
        assert trace.ok is False
        assert trace.tool_names == []

    def test_a_trace_with_an_answer_is_ok(self):
        trace = AgentTrace(answer="bonjour")
        assert trace.ok is True

    def test_the_content_of_a_step_is_truncated(self):
        """A huge tool result must not blow up the trace."""
        trace = AgentTrace()
        step = trace.add("observation", name="big", content="x" * 5000)

        assert len(step.content) <= 600

