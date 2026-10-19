"""Detector tests: shared fakes + registry/import checks (part 1 of 3)."""
import asyncio

from controllers import LOGIC
from detectors import BaseDetector, DetectionResult
from detectors.prefix.crit import crit
from detectors.prefix.gamble import gamble
from detectors.prefix.incscore import incscore


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


def check_imports():
    """The whole MVC + detectors stack must import cleanly and registries full."""
    import config.settings
    import config.start
    import config.utils
    import controllers
    import controllers.commands
    import detectors
    import detectors.base
    import detectors.prefix.detector
    import detectors.prefix.dm.router
    import detectors.prefix.router
    import detectors.slash.detector
    import models.db
    import models.duels
    import models.stats
    import views.challenge
    import views.formatting
    import views.leaderboard
    from detectors.prefix.dm.router import DMS_HANDLERS
    from detectors.prefix.router import COMMAND_HANDLERS

    expected = {"inc", "random", "aup", "clean", "incscore", "commands", "gamble", "crit", "chat"}
    assert expected.issubset(set(COMMAND_HANDLERS)), set(COMMAND_HANDLERS)
    assert set(DMS_HANDLERS) == {"commands"}, set(DMS_HANDLERS)
    assert len(LOGIC) == 9, sorted(LOGIC)


def check_registry():
    """LOGIC must expose every cmd_* function."""
    for name in ("cmd_inc", "cmd_random", "cmd_aup", "cmd_clean", "cmd_incscore",
                 "cmd_gamble", "cmd_crit", "cmd_help"):
        assert name in LOGIC, name
    assert gamble().logic_key is None
    assert crit().logic_key is None
    assert incscore().logic_key is None
