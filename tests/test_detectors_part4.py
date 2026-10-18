"""Detector tests: PrefixDetector steps + handle_message routing (part 4 of 4)."""
import asyncio

from detectors import BaseDetector, DetectionResult, PrefixDetector
from detectors.prefix.detector import handle_message
from tests.test_detectors_part1 import FakeBot, FakeChannel, FakeAuthor, make_message


def check_prefix_detector_steps():
    """Each ``!`` detection step classifies correctly; misses stop silently."""
    from detectors.prefix.dm.router import handle_command as handle_dm_command
    from detectors.prefix.router import handle_command as handle_guild_command

    bot = FakeBot()
    detector = PrefixDetector()

    own = make_message("!inc", author=bot.user)
    result = asyncio.run(detector.detect(own, bot))
    assert isinstance(detector, BaseDetector) and detector.name == "!"
    assert isinstance(result, DetectionResult)
    assert result.handled is False and result.proceed is False

    dm_channel = FakeChannel()
    dm_author = FakeAuthor(dm_channel=dm_channel)
    dm_message = make_message("!hot 10 2", author=dm_author, channel=dm_channel)
    result = asyncio.run(detector.detect(dm_message, bot))
    assert result.handled is True
    assert result.extra["dm"] is True
    assert result.handler is handle_dm_command
    assert result.command == "hot" and result.args == ["10", "2"]

    guild_message = make_message("!GAMBLE 50")
    result = asyncio.run(detector.detect(guild_message, bot))
    assert result.extra["dm"] is False
    assert result.handler is handle_guild_command
    assert result.command == "gamble" and result.args == ["50"]

    for content in ("hello", "!", ""):
        result = asyncio.run(detector.detect(make_message(content), bot))
        assert result.handled is False, content
        assert result.command is None


def check_prefix_detector_dispatch():
    """``handle_message`` must call the routed handler; misses stay silent."""
    from detectors.prefix.router import COMMAND_HANDLERS
    from detectors.prefix.dm.router import DMS_HANDLERS

    seen = []

    async def fake_guild_handler(command, args, message, bot_client):
        seen.append(("guild", command, args))

    async def fake_dm_handler(command, args, message, bot_client):
        seen.append(("dm", command, args))

    detector = PrefixDetector()
    orig_guild = COMMAND_HANDLERS.get("inc")
    orig_dm = DMS_HANDLERS.get("hot")

    class FakeGuildCmd:
        params = None

        async def handle(self, args, message, bot_client):
            await fake_guild_handler("inc", args, message, bot_client)

    class FakeDmCmd:
        params = None

        async def handle(self, args, message, bot_client):
            await fake_dm_handler("hot", args, message, bot_client)

    COMMAND_HANDLERS["inc"] = FakeGuildCmd()
    DMS_HANDLERS["hot"] = FakeDmCmd()
    try:
        bot = FakeBot()
        asyncio.run(handle_message(make_message("!inc"), bot, detector=detector))
        dm_channel = FakeChannel()
        dm_author = FakeAuthor(dm_channel=dm_channel)
        asyncio.run(handle_message(
            make_message("!hot 1 2", author=dm_author, channel=dm_channel),
            bot, detector=detector,
        ))
        asyncio.run(handle_message(make_message("hello"), bot, detector=detector))
        asyncio.run(handle_message(make_message("!inc", author=bot.user), bot, detector=detector))
    finally:
        if orig_guild is None:
            COMMAND_HANDLERS.pop("inc", None)
        else:
            COMMAND_HANDLERS["inc"] = orig_guild
        if orig_dm is None:
            DMS_HANDLERS.pop("hot", None)
        else:
            DMS_HANDLERS["hot"] = orig_dm

    assert seen == [("guild", "inc", []), ("dm", "hot", ["1", "2"])], seen


def check_legacy_imports_are_gone():
    """Old flat modules no longer exist after the detectors refactor."""
    import importlib.util
    assert importlib.util.find_spec("command_logic") is None
    assert importlib.util.find_spec("database_init") is None
    assert importlib.util.find_spec("message_handler") is None
    assert importlib.util.find_spec("dms_handler") is None
    assert importlib.util.find_spec("slash_commands") is None
    assert importlib.util.find_spec("settings") is None
    assert importlib.util.find_spec("utils") is None
    assert importlib.util.find_spec("commands") is None
    assert importlib.util.find_spec("dms") is None
    assert importlib.util.find_spec("filters") is None
