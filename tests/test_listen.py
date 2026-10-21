"""Tests for the listening transport — the bot answering a whole channel.

The listen controller is what makes the bot answer *every* message of the
channel it listens to.  These tests lock down the behaviour that keeps
that mode sane: it only answers the right channel, it never answers
itself, and it answers the messages of a channel one after the other.
"""
from __future__ import annotations

import asyncio

import pytest

from tetrabot.controllers import listen as listen_mod
from tetrabot.controllers.listen import ListenController
from tetrabot.controllers.listen import handle_message as handle_listen_message


class FakeAuthor:
    def __init__(self, name="alice", user_id=1, bot=False):
        self.name = name
        self.display_name = name
        self.id = user_id
        self.mention = f"<@{user_id}>"
        self.bot = bot
        self.dm_channel = None


class FakeBot:
    def __init__(self, user=None):
        self.user = user or FakeAuthor("BOT", 0, bot=True)


class FakeChannel:
    def __init__(self, name="Tetrabot", channel_id=42):
        self.name = name
        self.id = channel_id
        self.sent: list[dict] = []
        #: The messages the channel received, with their edits.
        self.messages: list[FakeSentMessage] = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        message = FakeSentMessage()
        self.messages.append(message)
        return message

    def history(self, limit=100):
        return _EmptyHistory()


class FakeSentMessage:
    def __init__(self):
        self.edits: list[dict] = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class _EmptyHistory:
    def __aiter__(self):
        async def gen():
            if False:  # pragma: no cover - never yields
                yield None

        return gen()


def make_message(content, channel=None, author=None):
    return type(
        "FakeMessage",
        (),
        {
            "content": content,
            "author": author or FakeAuthor(),
            "channel": channel or FakeChannel(),
        },
    )()


class TestListenDetection:
    @pytest.fixture
    def controller(self):
        return ListenController(channel_name="Tetrabot")

    def test_a_message_of_the_channel_is_handled(self, controller):
        bot = FakeBot()
        message = make_message("bonjour", channel=FakeChannel("Tetrabot"))
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is True
        assert result.args == ["bonjour"]

    def test_the_channel_name_is_case_insensitive(self, controller):
        bot = FakeBot()
        message = make_message("bonjour", channel=FakeChannel("tetrabot"))
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is True

    def test_another_channel_is_ignored(self, controller):
        bot = FakeBot()
        message = make_message("bonjour", channel=FakeChannel("general"))
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is False
        assert result.args == []

    def test_the_bot_ignores_its_own_messages(self, controller):
        """The bot must never answer its own answers."""
        bot = FakeBot()
        message = make_message(
            "bonjour",
            channel=FakeChannel("Tetrabot"),
            author=bot.user,
        )
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is False

    def test_an_empty_message_is_ignored(self, controller):
        bot = FakeBot()
        message = make_message("   ", channel=FakeChannel("Tetrabot"))
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is False

    @pytest.mark.parametrize("content", ["!inc", "/commands"])
    def test_a_command_is_left_to_the_command_controllers(self, controller, content):
        """A command must not be answered by the chatbot as well."""
        bot = FakeBot()
        message = make_message(content, channel=FakeChannel("Tetrabot"))
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is False

    def test_the_controller_is_a_base_controller(self, controller):
        from tetrabot.controllers.base import BaseController

        assert isinstance(controller, BaseController)
        assert controller.name == "listen"


class TestListenQueue:
    def test_the_messages_of_a_channel_are_answered_in_order(self):
        """A local model is never asked two questions at the same time."""
        order: list[str] = []
        queue = listen_mod.ChannelQueue()

        async def job(name):
            order.append(f"start {name}")
            await asyncio.sleep(0)
            order.append(f"end {name}")

        async def run():
            queue.submit(1, lambda: job("a"))
            queue.submit(1, lambda: job("b"))
            # Let the worker drain the queue.
            await asyncio.sleep(0.05)

        asyncio.run(run())

        assert order == ["start a", "end a", "start b", "end b"]

    def test_a_failing_job_does_not_kill_the_worker(self):
        """One broken answer must not silence the whole channel."""
        done: list[str] = []
        queue = listen_mod.ChannelQueue()

        async def boom():
            raise RuntimeError("boom")

        async def job():
            done.append("answered")

        async def run():
            queue.submit(1, boom)
            queue.submit(1, job)
            await asyncio.sleep(0.05)

        asyncio.run(run())

        assert done == ["answered"]


class TestListenDispatch:
    def test_a_message_reaches_the_chatbot_handler(self, monkeypatch):
        """The listening transport runs the shared chatbot behaviour."""
        seen: dict = {}

        async def fake_handler(ctx):
            seen["args"] = list(ctx.args)
            seen["prefix"] = ctx.prefix

        from tetrabot.controllers import base

        monkeypatch.setitem(base.HANDLERS, "cmd_listen", fake_handler)

        bot = FakeBot()
        channel = FakeChannel("Tetrabot")
        message = make_message("salut", channel=channel)

        async def run():
            controller = ListenController(channel_name="Tetrabot")
            await handle_listen_message(message, bot, controller=controller)
            # The answer is queued: wait for the worker to finish.
            await asyncio.sleep(0.05)

        asyncio.run(run())

        assert seen["args"] == ["salut"]
        assert seen["prefix"] == "listen"

    def test_a_message_of_another_channel_is_not_answered(self, monkeypatch):
        from tetrabot.controllers import base

        called: list[str] = []

        async def fake_handler(ctx):
            called.append("answered")

        monkeypatch.setitem(base.HANDLERS, "cmd_listen", fake_handler)

        bot = FakeBot()
        message = make_message("salut", channel=FakeChannel("general"))

        async def run():
            controller = ListenController(channel_name="Tetrabot")
            await handle_listen_message(message, bot, controller=controller)
            await asyncio.sleep(0.05)

        asyncio.run(run())

        assert called == []


class TestListenEndToEnd:
    """The whole path: a message in the channel → an answer in the channel."""

    def test_a_message_produces_an_answer(self, monkeypatch):
        from tetrabot.controllers.commands import chat as chat_cmd

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield "bonjour"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd.config, "CHAT_STREAM", True)
        monkeypatch.setattr(chat_cmd.config, "CHAT_EDIT_INTERVAL", 0.0)

        bot = FakeBot()
        channel = FakeChannel("Tetrabot")
        message = make_message("salut", channel=channel)

        async def run():
            controller = ListenController(channel_name="Tetrabot")
            await handle_listen_message(message, bot, controller=controller)
            await asyncio.sleep(0.05)

        asyncio.run(run())

        # The bot posted one message, then rewrote it into the answer.
        assert len(channel.sent) == 1
        assert "réfléchis" in channel.sent[0]["content"]
        assert len(channel.messages) == 1
        assert channel.messages[0].edits[-1]["content"] == "> 🤖 bonjour"

    def test_the_answer_is_remembered(self, monkeypatch):
        """The next message of the channel builds on the previous one."""
        from tetrabot.controllers.commands import chat as chat_cmd

        async def fake_stream(prompt, context=None, system=None, **kwargs):
            yield "je m'appelle Tetrabot"

        monkeypatch.setattr(chat_cmd.llm, "stream_complete", fake_stream)
        monkeypatch.setattr(chat_cmd.config, "CHAT_STREAM", True)
        monkeypatch.setattr(chat_cmd.config, "CHAT_EDIT_INTERVAL", 0.0)

        bot = FakeBot()
        channel = FakeChannel("Tetrabot")
        message = make_message("comment tu te nommes ?", channel=channel)

        async def run():
            controller = ListenController(channel_name="Tetrabot")
            await handle_listen_message(message, bot, controller=controller)
            await asyncio.sleep(0.05)

        asyncio.run(run())

        remembered = chat_cmd.MEMORY.context(channel.id, 20)
        assert any("comment tu te nommes ?" in line for line in remembered)
        assert any("Tetrabot" in line for line in remembered)
