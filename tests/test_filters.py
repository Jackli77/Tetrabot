"""FILTERS layer tests: each gate classifies messages, the pipeline chains them.

Uses fake Message/Bot objects — no Discord connection involved.
"""
import asyncio

from controllers.dm.router import handle_command as handle_dm_command
from controllers.prefix.router import handle_command as handle_guild_command
from filters import (
    DirectMessageFilter,
    FilterPipeline,
    FilterResult,
    IgnoreSelfFilter,
    PrefixFilter,
    default_pipeline,
)


class FakeAuthor:
    def __init__(self, name="alice", dm_channel=None):
        self.name = name
        self.dm_channel = dm_channel


class FakeBot:
    def __init__(self, user="BOT"):
        self.user = user


class FakeChannel:
    pass


def make_message(content, author=None, channel=None, dm_channel=None):
    author = author or FakeAuthor(dm_channel=dm_channel)
    return type(
        "FakeMessage",
        (),
        {"content": content, "author": author, "channel": channel or FakeChannel()},
    )()


def run():
    bot = FakeBot()

    # --- IgnoreSelfFilter ----------------------------------------------------
    own = make_message("!inc", author=bot.user)
    result = asyncio.run(IgnoreSelfFilter().apply(own, bot, FilterResult()))
    assert result.proceed is False

    other = make_message("!inc", author="alice")
    result = asyncio.run(IgnoreSelfFilter().apply(other, bot, FilterResult()))
    assert result.proceed is True

    # --- DirectMessageFilter -------------------------------------------------
    dm_channel = FakeChannel()
    dm_author = FakeAuthor(dm_channel=dm_channel)
    dm_message = make_message("!hot 10 2", author=dm_author, channel=dm_channel)
    result = asyncio.run(DirectMessageFilter().apply(dm_message, bot, FilterResult()))
    assert result.proceed is True
    assert result.extra["dm"] is True
    assert result.handler is handle_dm_command

    guild_message = make_message("!inc")
    result = asyncio.run(DirectMessageFilter().apply(guild_message, bot, FilterResult()))
    assert result.extra["dm"] is False
    assert result.handler is handle_guild_command

    # --- PrefixFilter --------------------------------------------------------
    result = asyncio.run(PrefixFilter().apply(make_message("!gamble 50"), bot, FilterResult()))
    assert result.proceed is True
    assert result.command == "gamble" and result.args == ["50"]

    result = asyncio.run(PrefixFilter().apply(make_message("!GAMBLE 50"), bot, FilterResult()))
    assert result.command == "gamble"  # command names are lowercased

    for content in ("hello", "!", ""):
        result = asyncio.run(PrefixFilter().apply(make_message(content), bot, FilterResult()))
        assert result.proceed is False, content

    # --- FilterPipeline ------------------------------------------------------
    pipeline = FilterPipeline(IgnoreSelfFilter(), DirectMessageFilter(), PrefixFilter())
    result = asyncio.run(pipeline.run(make_message("!inc"), bot))
    assert result.proceed is True
    assert result.command == "inc" and result.args == []
    assert result.handler is handle_guild_command

    # A stopped pipeline never reaches later filters.
    result = asyncio.run(pipeline.run(make_message("hello"), bot))
    assert result.proceed is False
    assert result.command is None

    # --- default_pipeline ----------------------------------------------------
    assert isinstance(default_pipeline(), FilterPipeline)
    result = asyncio.run(default_pipeline().run(make_message("!inc"), bot))
    assert result.proceed is True and result.command == "inc"

    result = asyncio.run(default_pipeline().run(make_message("!inc", author=bot.user), bot))
    assert result.proceed is False  # the bot's own messages are dropped first

    print("test_filters: all passed")
