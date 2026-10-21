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

from .conftest import FakeUser


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


class TestChatCommand:
    def test_streams_the_answer_into_the_channel(self, make_ctx, patch_config, monkeypatch):
        """The answer is written progressively, into a single message."""
        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield "bon"
            yield "jour"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        # The placeholder is sent first, then the streamed edits.
        assert "réfléchis" in responder.sent[0]["content"]
        assert responder.edits, "the answer should have been streamed"
        assert responder.edited_contents[-1] == "> 🤖 bonjour"
        # The answer replaces the placeholder: it is not posted twice.
        assert len(responder.sent) == 1

    def test_asks_the_model_with_the_user_message(self, make_ctx, patch_config, monkeypatch):
        seen = {}

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            seen["prompt"] = prompt
            seen["system"] = system
            yield "ok"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert seen["prompt"] == "salut"
        assert "Tetrabot" in seen["system"]

    def test_remembers_the_exchange(self, make_ctx, patch_config, monkeypatch):
        """The next question can build on what was said before."""
        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield "je m'appelle Tetrabot"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, _ = make_ctx(author=FakeUser(1, "alice"), args=["comment tu te nommes ?"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        remembered = chat_cmd.MEMORY.context(ctx.channel.id, 20)
        assert any("comment tu te nommes ?" in line for line in remembered)
        assert any("Tetrabot" in line for line in remembered)

    def test_an_empty_answer_is_retried(self, make_ctx, patch_config, monkeypatch):
        """A thinking model that runs out of budget gets a second chance."""
        calls = []

        async def fake_stream(prompt, context=None, system=None, **kwargs):
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
        async def fake_stream(prompt, context=None, system=None, **kwargs):
            raise llm.OllamaUnavailable("cannot reach Ollama")
            yield  # pragma: no cover - never reached

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert "Ollama ne répond pas" in responder.sent[-1]["content"]

    def test_a_missing_model_is_reported_clearly(self, make_ctx, patch_config, monkeypatch):
        async def fake_stream(prompt, context=None, system=None, **kwargs):
            raise llm.OllamaModelMissing("model not installed")
            yield  # pragma: no cover - never reached

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        assert "Modèle introuvable" in responder.sent[-1]["content"]

    def test_a_long_answer_becomes_an_embed(self, make_ctx, patch_config, monkeypatch):
        long_answer = "a" * (chat_cmd.EMBED_THRESHOLD + 100)

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield long_answer

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["raconte"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))

        # The long answer replaces the streamed text with an embed.
        assert responder.edits[-1]["embed"] is not None

    def test_an_empty_message_is_ignored(self, make_ctx, patch_config):
        """An empty message has nothing to answer."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=[""])
        asyncio.run(chat_cmd.cmd_listen(ctx))
        assert responder.sent == []

    def test_forget_clears_the_memory(self, make_ctx, patch_config, monkeypatch):
        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield "ok"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)

        ctx, _ = make_ctx(author=FakeUser(1, "alice"), args=["salut"])
        ctx.channel = FakeHistoryChannel()
        asyncio.run(chat_cmd.cmd_listen(ctx))
        assert chat_cmd.MEMORY.context(ctx.channel.id, 20)

        asyncio.run(chat_cmd.cmd_forget(ctx))
        assert chat_cmd.MEMORY.context(ctx.channel.id, 20) == []
