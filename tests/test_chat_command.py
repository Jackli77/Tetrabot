"""End-to-end tests of the chat command itself.

They drive ``cmd_listen`` with a fake model, so the whole flow is exercised:
the acknowledgement, the streaming edits, the retry on an empty answer, the
memory and the final rendering.
"""
from __future__ import annotations

import asyncio

import pytest

from tetrabot.controllers.commands import chat as chat_cmd
from tetrabot.models import llm
from tetrabot.models.agent import Agent

from .conftest import FakeModel, FakeUser


class FakeHistory:
    """An async iterator over fake channel messages."""

    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        async def gen():
            for message in self._messages:
                yield message

        return gen()


class FakeHistoryMessage:
    def __init__(self, author, content):
        self.author = FakeUser(1, author)
        self.content = content


class FakeHistoryChannel:
    """A channel whose history is newest-first, like Discord's."""

    def __init__(self, messages=()):
        self._messages = list(messages)
        self.id = 42

    def history(self, limit=100):
        return FakeHistory(self._messages[:limit])


@pytest.fixture(autouse=True)
def clean_memory():
    """Each test starts with an empty memory."""
    chat_cmd.MEMORY._conversations.clear()
    yield
    chat_cmd.MEMORY._conversations.clear()


@pytest.fixture
def patch_config(monkeypatch):
    """Force the deterministic settings the tests need."""
    monkeypatch.setattr(chat_cmd.config, "CHAT_STREAM", True)
    monkeypatch.setattr(chat_cmd.config, "CHAT_EDIT_INTERVAL", 0.0)
    monkeypatch.setattr(chat_cmd.config, "CHAT_CONTEXT_MESSAGES", 5)
    return monkeypatch


@pytest.fixture
def scripted_agent(monkeypatch):
    """Make the chatbot use a scripted model instead of Ollama.

    The script is a list of ``(text, [(tool, arguments), ...])`` turns; the
    last one is repeated when the script runs out.
    """

    def _install(script):
        model = FakeModel(script)
        monkeypatch.setattr(
            chat_cmd, "Agent", lambda **kwargs: Agent(backend=model, **kwargs)
        )
        return model

    return _install


class TestChatCommand:
    def test_streams_the_answer_into_the_channel(self, make_ctx, patch_config, scripted_agent):
        """The answer is written progressively, into a single message."""
        scripted_agent([("bonjour", [])])

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        # The placeholder is sent first, then the streamed edits.
        assert "réfléchis" in responder.sent[0]["content"]
        assert responder.edits, "the answer should have been streamed"
        assert responder.edited_contents[-1] == "> 🤖 bonjour"
        # The answer replaces the placeholder: it is not posted twice.
        assert len(responder.sent) == 1

    def test_asks_the_model_with_the_user_message(self, make_ctx, patch_config, scripted_agent):
        model = scripted_agent([("ok", [])])

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert model.rounds[0][-1]["content"] == "salut"

    def test_remembers_the_exchange(self, make_ctx, patch_config, scripted_agent):
        """The next question can build on what was said before."""
        scripted_agent([("je m'appelle Tetrabot", [])])

        ctx, _ = make_ctx(author=FakeUser(1, "alice"), args=["comment tu te nommes ?"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        remembered = chat_cmd.MEMORY.context(ctx.channel.id, 20)
        assert any("comment tu te nommes ?" in line for line in remembered)
        assert any("Tetrabot" in line for line in remembered)

    def test_an_empty_answer_is_retried(self, make_ctx, patch_config, monkeypatch):
        """A thinking model that runs out of budget gets a second chance."""
        calls = []

        async def fake_stream(messages=None, tools=None, system=None, **kwargs):
            calls.append("stream")
            return
            yield  # pragma: no cover - never reached

        async def fake_complete(prompt=None, context=None, system=None, **kwargs):
            calls.append("complete")
            return chat_cmd.llm.Completion(content="une vraie reponse")

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd.llm, "complete", fake_complete)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert calls == ["stream", "complete"]
        assert responder.edited_contents[-1] == "> 🤖 une vraie reponse"

    def test_a_dead_server_is_reported_clearly(self, make_ctx, patch_config, monkeypatch):
        async def fake_stream(messages=None, tools=None, system=None, **kwargs):
            raise llm.OllamaUnavailable("cannot reach Ollama")
            yield  # pragma: no cover - never reached

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert "Ollama ne répond pas" in responder.sent[-1]["content"]

    def test_a_missing_model_is_reported_clearly(self, make_ctx, patch_config, monkeypatch):
        async def fake_stream(messages=None, tools=None, system=None, **kwargs):
            raise llm.OllamaModelMissing("model not installed")
            yield  # pragma: no cover - never reached

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert "Modèle introuvable" in responder.sent[-1]["content"]

    def test_a_long_answer_becomes_an_embed(self, make_ctx, patch_config, scripted_agent):
        long_answer = "a" * (chat_cmd.EMBED_THRESHOLD + 100)
        scripted_agent([(long_answer, [])])

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["raconte"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        # The long answer replaces the streamed text with an embed.
        assert responder.edits[-1]["embed"] is not None

    def test_an_empty_message_is_ignored(self, make_ctx, patch_config, scripted_agent):
        """An empty message has nothing to answer."""
        scripted_agent([("ok", [])])
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=[""])
        asyncio.run(chat_cmd.cmd_listen(ctx))
        assert responder.sent == []

    def test_the_answer_can_be_produced_without_streaming(self, make_ctx, patch_config, scripted_agent, monkeypatch):
        """With streaming off, the answer is produced in one go."""
        monkeypatch.setattr(chat_cmd.config, "CHAT_STREAM", False)
        scripted_agent([("bonjour", [])])

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert responder.edited_contents[-1] == "> 🤖 bonjour"

    def test_the_trace_is_kept(self, make_ctx, patch_config, scripted_agent):
        """The trace of the run is kept, so ``/trace`` can show it."""
        scripted_agent([("ok", [])])

        ctx, _ = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        trace = chat_cmd.LAST_TRACES.get(ctx.channel.id)
        assert trace is not None
        assert trace.answer == "ok"

    def test_the_trace_command_shows_the_last_run(self, make_ctx, patch_config, scripted_agent):
        """``/trace`` shows how the last answer was found."""
        scripted_agent(
            [
                ("Je regarde.", [("get_weather", {"city": "Paris"})]),
                ("Il fait 14 degres.", []),
            ]
        )

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["meteo ?"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))
        responder.sent.clear()

        asyncio.run(chat_cmd.cmd_trace(ctx))

        assert responder.sent, "the trace should have been sent"
        embed = responder.sent[-1]["embed"]
        assert embed is not None
        assert embed.title == "🧠 Trace de l'agent"
        # The tool that was called is visible in the trace.
        assert any("get_weather" in field.name for field in embed.fields)

    def test_the_trace_command_says_when_there_is_nothing(self, make_ctx, patch_config):
        """Without a run, the command says so instead of failing."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["/trace"])
        ctx.channel = FakeHistoryChannel()
        chat_cmd.LAST_TRACES.pop(ctx.channel.id, None)

        asyncio.run(chat_cmd.cmd_trace(ctx))

        assert "Aucun agent" in responder.sent[-1]["content"]

    def test_forget_clears_the_memory(self, make_ctx, patch_config, scripted_agent):
        scripted_agent([("ok", [])])

        ctx, _ = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))
        assert chat_cmd.MEMORY.context(ctx.channel.id, 20)

        asyncio.run(chat_cmd.cmd_forget(ctx))
        assert chat_cmd.MEMORY.context(ctx.channel.id, 20) == []
