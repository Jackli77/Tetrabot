"""Tests for the tool-calling loop of the chatbot.

The model asks for a tool, the bot runs it, feeds the result back, and the
model writes the final answer.  These tests drive that loop with a fake
model, so no network and no real model are needed.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from tetrabot.controllers.commands import chat as chat_cmd
from tetrabot.models import llm

from .conftest import FakeUser


@pytest.fixture(autouse=True)
def clean_memory():
    chat_cmd.MEMORY._conversations.clear()
    yield
    chat_cmd.MEMORY._conversations.clear()


@pytest.fixture
def patch_config(monkeypatch):
    monkeypatch.setattr(chat_cmd.config, "CHAT_STREAM", True)
    monkeypatch.setattr(chat_cmd.config, "CHAT_EDIT_INTERVAL", 0.0)
    monkeypatch.setattr(chat_cmd.config, "CHAT_MAX_TOOL_ROUNDS", 3)
    return monkeypatch


def build_ctx(make_ctx_fixture, args):
    """A context with a channel that has no history."""
    ctx, responder = make_ctx_fixture(author=FakeUser(1, "alice"), args=args)
    ctx.channel = type("Ch", (), {"id": 42, "history": lambda self, limit=100: _empty()})()
    return ctx, responder


def _empty():
    class It:
        def __aiter__(self):
            async def gen():
                if False:
                    yield None

            return gen()

    return It()


class TestToolLoop:
    def test_a_tool_is_run_and_its_result_is_fed_back(self, make_ctx, patch_config, monkeypatch):
        """The model asks for the weather, the tool runs, the model answers."""
        rounds = []

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            rounds.append(kwargs.get("messages") or [])
            if len(rounds) == 1:
                yield llm.ToolCall(name="get_weather", arguments={"city": "Paris"}, id="c1")
            else:
                yield "Il fait 14 degres a Paris."

        async def fake_tool(call):
            return json.dumps({"ok": True, "result": {"temperature_c": 14}})

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd, "_run_tool", fake_tool)

        ctx, responder = build_ctx(make_ctx, ["Quel temps fait-il a Paris ?"])
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert len(rounds) == 2, "the model should be asked twice"
        # The second round carries the tool result.
        assert rounds[1][-1]["role"] == "tool"
        assert "14" in rounds[1][-1]["content"]
        assert responder.edited_contents[-1] == "> 🤖 Il fait 14 degres a Paris."

    def test_several_tools_at_once_are_all_run(self, make_ctx, patch_config, monkeypatch):
        """The model may ask for two tools in the same turn."""
        rounds = []
        ran = []

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            rounds.append(kwargs.get("messages") or [])
            if len(rounds) == 1:
                yield llm.ToolCall(name="get_weather", arguments={"city": "Paris"}, id="c1")
                yield llm.ToolCall(name="get_datetime", arguments={}, id="c2")
            else:
                yield "Voici."

        async def fake_tool(call):
            ran.append(call.name)
            return json.dumps({"ok": True, "result": {}})

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd, "_run_tool", fake_tool)

        ctx, responder = build_ctx(make_ctx, ["Meteo et heure ?"])
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert ran == ["get_weather", "get_datetime"]
        # Both results are fed back, one tool message each.
        tool_messages = [m for m in rounds[1] if m["role"] == "tool"]
        assert len(tool_messages) == 2

    def test_the_tool_call_message_has_the_right_shape(self, make_ctx, patch_config, monkeypatch):
        """The assistant message must hold every call of the turn."""
        rounds = []

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            rounds.append(kwargs.get("messages") or [])
            if len(rounds) == 1:
                yield llm.ToolCall(name="get_weather", arguments={"city": "Paris"}, id="c1")
                yield llm.ToolCall(name="get_datetime", arguments={}, id="c2")
            else:
                yield "ok"

        async def fake_tool(call):
            return "{}"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd, "_run_tool", fake_tool)

        ctx, _ = build_ctx(make_ctx, ["question"])
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assistant = [m for m in rounds[1] if m["role"] == "assistant"]
        assert len(assistant) == 1
        calls = assistant[0]["tool_calls"]
        assert len(calls) == 2
        # The id belongs to the call, not to the function: Ollama answers
        # with a 500 when it is nested one level too deep.
        assert calls[0]["id"] == "c1"
        assert calls[0]["function"]["name"] == "get_weather"

    def test_an_unknown_tool_is_reported_to_the_model(self, make_ctx, patch_config, monkeypatch):
        """A tool that does not exist produces a message, not a crash."""
        result = asyncio.run(chat_cmd._run_tool(llm.ToolCall(name="nope", arguments={})))
        payload = json.loads(result)
        assert payload["ok"] is False
        assert "nope" in payload["error"]

    def test_the_loop_stops_after_the_maximum_rounds(self, make_ctx, patch_config, monkeypatch):
        """A model that keeps asking for tools is stopped."""
        rounds = []

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            rounds.append(1)
            yield llm.ToolCall(name="get_weather", arguments={"city": "Paris"})

        async def fake_tool(call):
            return "{}"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd, "_run_tool", fake_tool)

        ctx, responder = build_ctx(make_ctx, ["boucle"])
        asyncio.run(chat_cmd.cmd_listen(ctx))

        # CHAT_MAX_TOOL_ROUNDS is 3, so at most 4 rounds are asked.
        assert len(rounds) <= 4

    def test_the_tool_schemas_are_offered_to_the_model(self, make_ctx, patch_config, monkeypatch):
        seen = {}

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            seen["tools"] = kwargs.get("tools")
            yield "ok"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, _ = build_ctx(make_ctx, ["salut"])
        asyncio.run(chat_cmd.cmd_listen(ctx))

        names = {t["function"]["name"] for t in seen["tools"]}
        assert "get_weather" in names
        assert "search_wikipedia" in names
