"""Tests for the ``!`` prefix detector and the slash detector."""
from __future__ import annotations

import asyncio

import pytest

from tetrabot.context import CommandContext, PrefixResponder, SlashResponder
from tetrabot.detectors import BaseDetector, DetectionResult, PrefixDetector
from tetrabot.detectors.prefix import handle_message


class FakeAuthor:
    def __init__(self, name="alice", dm_channel=None):
        self.name = name
        self.display_name = name
        self.id = 1
        self.mention = "<@1>"
        self.dm_channel = dm_channel


class FakeBot:
    def __init__(self, user="BOT"):
        self.user = user


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        return FakeSentMessage()


class FakeSentMessage:
    async def delete(self):
        return None


def make_message(content, author=None, channel=None, dm_channel=None):
    author = author or FakeAuthor(dm_channel=dm_channel)
    return type(
        "FakeMessage",
        (),
        {"content": content, "author": author, "channel": channel or FakeChannel()},
    )()


class TestPrefixDetection:
    @pytest.fixture
    def detector(self):
        return PrefixDetector()

    def test_ignores_its_own_messages(self, detector):
        bot = FakeBot()
        result = asyncio.run(detector.detect(make_message("!inc", author=bot.user), bot))
        assert result.handled is False
        assert result.command is None

    def test_detects_a_dm(self, detector):
        bot = FakeBot()
        dm_channel = FakeChannel()
        message = make_message(
            "!commands", author=FakeAuthor(dm_channel=dm_channel), channel=dm_channel
        )
        result = asyncio.run(detector.detect(message, bot))
        assert result.handled is True
        assert result.is_dm is True
        assert result.command == "commands"
        assert result.args == []

    def test_detects_a_guild_command(self, detector):
        bot = FakeBot()
        result = asyncio.run(detector.detect(make_message("!GAMBLE 50"), bot))
        assert result.is_dm is False
        assert result.command == "gamble"
        assert result.args == ["50"]

    @pytest.mark.parametrize("content", ["hello", "!", ""])
    def test_ignores_non_commands(self, detector, content):
        bot = FakeBot()
        result = asyncio.run(detector.detect(make_message(content), bot))
        assert result.handled is False
        assert result.command is None

    def test_result_is_a_detection_result(self, detector):
        bot = FakeBot()
        result = asyncio.run(detector.detect(make_message("!inc"), bot))
        assert isinstance(result, DetectionResult)
        assert isinstance(detector, BaseDetector)
        assert detector.name == "!"


class TestPrefixDispatch:
    def test_unknown_command_is_ignored(self):
        bot = FakeBot()
        channel = FakeChannel()
        message = make_message("!nope", channel=channel)
        asyncio.run(handle_message(message, bot))
        assert channel.sent == []

    def test_missing_arguments_are_reported(self):
        bot = FakeBot()
        channel = FakeChannel()
        message = make_message("!gamble", channel=channel)
        asyncio.run(handle_message(message, bot))
        assert len(channel.sent) == 1
        assert "minimum 1 arguments" in channel.sent[0]["content"]


class FakeSlashInteraction:
    """A minimal stand-in for a Discord interaction."""

    def __init__(self):
        self.user = FakeAuthor()
        self.channel = FakeChannel()
        self.client = object()
        self.response = FakeResponse()
        self.followup = FakeFollowup(self.response)


class FakeResponse:
    def __init__(self):
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(("response", kwargs))

    async def defer(self):
        self.calls.append(("defer", {}))

    def is_done(self):
        return bool(self.calls)


class FakeFollowup:
    def __init__(self, response):
        self.response = response

    async def send(self, **kwargs):
        self.response.calls.append(("followup", kwargs))


class TestResponders:
    def test_prefix_responder_posts_in_the_channel(self):
        channel = FakeChannel()
        message = make_message("!inc", channel=channel)
        responder = PrefixResponder(message)
        asyncio.run(responder(content="hello"))
        assert channel.sent[0]["content"] == "hello"

    def test_slash_responder_uses_response_then_followup(self):
        interaction = FakeSlashInteraction()
        responder = SlashResponder(interaction)
        asyncio.run(responder(content="first"))
        asyncio.run(responder(content="second", ephemeral=True))

        calls = interaction.response.calls
        assert calls[0][0] == "response"
        assert "ephemeral" not in calls[0][1]
        assert calls[1][0] == "followup"
        assert calls[1][1]["ephemeral"] is True

    def test_slash_responder_defer(self):
        interaction = FakeSlashInteraction()
        responder = SlashResponder(interaction)
        asyncio.run(responder.defer())
        asyncio.run(responder(content="after defer"))
        assert interaction.response.calls[0][0] == "defer"
        assert interaction.response.calls[1][0] == "followup"


class TestContext:
    def test_user_id_comes_from_the_author(self):
        ctx = CommandContext(
            author=FakeAuthor(), channel=None, client=None, args=[], respond=None
        )
        assert ctx.user_id == 1

    def test_is_slash_reflects_the_prefix(self):
        ctx = CommandContext(
            author=FakeAuthor(),
            channel=None,
            client=None,
            args=[],
            respond=None,
            prefix="/",
        )
        assert ctx.is_slash is True

