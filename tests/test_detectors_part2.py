"""Detector tests: ``!`` and ``/`` dispatch + contexts (part 2 of 3)."""
import asyncio

from controllers import LOGIC, CommandContext, make_prefix_respond, make_slash_respond
from controllers.context import CommandContext as ContextFromSubmodule
from detectors import SlashDetector
from detectors.prefix.base_command import BaseCommand
from detectors.slash.detector import build_context as build_slash_context
from detectors.slash.detector import setup_slash_commands


def check_prefix_dispatch():
    """The generic ``!`` adapter must route through LOGIC with a normalised ctx."""
    calls = []

    async def fake_logic(ctx):
        calls.append(ctx)

    class FakeCmd(BaseCommand):
        logic_key = "cmd_test"

        def __init__(self):
            super().__init__("test", [])

    class FakeMessage:
        author = "AUTHOR"
        channel = "CHANNEL"

    orig = LOGIC.get("cmd_test")
    LOGIC["cmd_test"] = fake_logic
    try:
        asyncio.run(FakeCmd().handle([], FakeMessage(), "CLIENT"))
    finally:
        if orig is None:
            del LOGIC["cmd_test"]
        else:
            LOGIC["cmd_test"] = orig

    assert len(calls) == 1
    ctx = calls[0]
    assert isinstance(ctx, CommandContext)
    assert ctx.author == "AUTHOR" and ctx.channel == "CHANNEL" and ctx.client == "CLIENT"
    assert ctx.args == [] and ctx.prefix == "!"


def check_context_normalisation():
    """Mention-based user_id must work for prefix-style authors."""
    class FakeUser:
        mention = "<@123456789012345678>"
        id = 123456789012345678

    async def noop(**kwargs):
        pass

    ctx = CommandContext(
        author=FakeUser(), channel=None, client=None, args=[],
        respond=noop, prefix="!",
    )
    assert ctx.user_id == 123456789012345678
    assert ContextFromSubmodule is CommandContext
