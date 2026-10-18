"""Transport wiring tests: prefix and slash adapters dispatch into LOGIC.

Uses fake Message/Interaction objects — no Discord connection or database
round-trips are involved.  Also runs a whole-package import check.
"""
import asyncio

from controllers import LOGIC, CommandContext, make_prefix_respond, make_slash_respond
from controllers.context import CommandContext as ContextFromSubmodule
from controllers.slash import build_context as build_slash_context
from controllers.slash import setup_slash_commands
from controllers.prefix.base_command import BaseCommand
from controllers.prefix.gamble import gamble
from controllers.prefix.crit import crit
from controllers.prefix.incscore import incscore


def check_imports():
    """The whole MVC stack must import cleanly and registries must be full."""
    import config.settings
    import config.start
    import config.utils
    import controllers
    import controllers.commands
    import controllers.dm.router
    import controllers.prefix.router
    import controllers.slash
    import filters.base
    import filters.direct_messages
    import filters.pipeline
    import filters.prefix
    import filters.self_messages
    import models.db
    import models.duels
    import models.stats
    import views.challenge
    import views.formatting
    import views.leaderboard
    from controllers.prefix.router import COMMAND_HANDLERS
    from controllers.dm.router import DMS_HANDLERS

    expected = {"inc", "random", "aup", "clean", "incscore", "commands", "gamble", "crit"}
    assert expected.issubset(set(COMMAND_HANDLERS)), set(COMMAND_HANDLERS)
    assert "hot" in DMS_HANDLERS and "commands" in DMS_HANDLERS
    assert len(LOGIC) == 8, sorted(LOGIC)
    assert "hot" not in LOGIC


def check_registry():
    """LOGIC must expose every cmd_* function, with aliasing for name mismatches."""
    for name in ("cmd_inc", "cmd_random", "cmd_aup", "cmd_clean", "cmd_incscore",
                 "cmd_gamble", "cmd_crit", "cmd_help"):
        assert name in LOGIC, name
    assert gamble().logic_key is None
    assert crit().logic_key is None
    assert incscore().logic_key is None


def check_prefix_dispatch():
    """The generic prefix handle() must route through LOGIC, and a
    CommandContext built from a Message must normalise fields correctly."""
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


def check_respond_factories():
    """Slash respond: first call uses interaction.response, later followups."""

    class FakeResponse:
        def __init__(self):
            self.calls = []

        async def send_message(self, **kwargs):
            self.calls.append(("response", kwargs))

        async def defer(self):
            self.calls.append(("defer", {}))

    class FakeFollowup:
        def __init__(self, response):
            self.response = response

        async def send(self, **kwargs):
            self.response.calls.append(("followup", kwargs))

    class FakeInteraction:
        def __init__(self):
            self.response = FakeResponse()
            self.followup = FakeFollowup(self.response)

    async def main():
        interaction = FakeInteraction()
        respond = make_slash_respond(interaction)
        await respond(content="first")
        await respond(content="second", ephemeral=True)
        return interaction.response.calls

    calls = asyncio.run(main())
    assert calls[0][0] == "response"
    assert calls[0][1]["content"] == "first"
    assert "ephemeral" not in calls[0][1]
    assert calls[1][0] == "followup"
    assert calls[1][1]["content"] == "second"
    assert calls[1][1]["ephemeral"] is True

    # Defer marks the interaction as used.
    async def main2():
        interaction = FakeInteraction()
        respond = make_slash_respond(interaction)
        await respond.defer()
        await respond(content="after defer")
        return interaction.response.calls

    calls2 = asyncio.run(main2())
    assert calls2[0][0] == "defer"
    assert calls2[1][0] == "followup"

    # Embed and view must be forwarded as-is (prefix transport).
    class FakeSentMessage:
        pass

    class FakeMessage:
        def __init__(self):
            self.sent = []

        async def send(self, **kwargs):
            self.sent.append(kwargs)
            return FakeSentMessage()

    class FakeChannel:
        def __init__(self, fake_message):
            self.fake_message = fake_message

        async def send(self, **kwargs):
            return await self.fake_message.send(**kwargs)

    class FakeMessageObj:
        author = "AUTHOR"

    message = FakeMessageObj()
    fake_message = FakeMessage()
    message.channel = FakeChannel(fake_message)
    sent = asyncio.run(make_prefix_respond(message)(content="hello", embed="EMBED", view="VIEW"))
    assert fake_message.sent[0]["content"] == "hello"
    assert fake_message.sent[0]["embed"] == "EMBED"
    assert fake_message.sent[0]["view"] == "VIEW"
    assert isinstance(sent, FakeSentMessage)


def check_slash_dispatch_and_context():
    """The slash tree must register 9 commands; build_context must
    produce a CommandContext with prefix '/' and the interaction's respond."""
    calls = []

    async def fake_logic(ctx):
        calls.append(ctx)

    class FakeTree:
        def __init__(self):
            self.commands = {}

        def command(self, *, name, description):
            def decorator(func):
                self.commands[name] = func
                return func
            return decorator

    class FakeInteraction:
        def __init__(self):
            self.user = "USER"
            self.channel = "CHANNEL"
            self.client = "CLIENT"

    tree = FakeTree()
    setup_slash_commands("BOT", tree)
    assert len(tree.commands) == 9, sorted(tree.commands)

    orig = LOGIC["cmd_inc"]
    LOGIC["cmd_inc"] = fake_logic
    try:
        asyncio.run(tree.commands["inc"](FakeInteraction()))
    finally:
        LOGIC["cmd_inc"] = orig

    assert len(calls) == 1
    ctx = calls[0]
    assert ctx.prefix == "/"
    assert ctx.author == "USER" and ctx.channel == "CHANNEL" and ctx.client == "CLIENT"

    # build_context passes args and wires make_slash_respond.
    ctx = build_slash_context(FakeInteraction(), args=["1", "100"])
    assert ctx.args == ["1", "100"]
    assert callable(ctx.respond)


def check_legacy_imports_are_gone():
    """Old flat modules no longer exist after the MVC refactor."""
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


def run():
    check_imports()
    check_registry()
    check_prefix_dispatch()
    check_context_normalisation()
    check_respond_factories()
    check_slash_dispatch_and_context()
    check_legacy_imports_are_gone()
    print("test_transport: all passed")
