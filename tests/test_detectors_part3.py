"""Detector tests: respond factories + slash tree wiring (part 3 of 3)."""
import asyncio

from controllers import LOGIC, make_prefix_respond, make_slash_respond
from detectors import SlashDetector
from detectors.slash.detector import build_context as build_slash_context
from detectors.slash.detector import setup_slash_commands


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

    async def main2():
        interaction = FakeInteraction()
        respond = make_slash_respond(interaction)
        await respond.defer()
        await respond(content="after defer")
        return interaction.response.calls

    calls2 = asyncio.run(main2())
    assert calls2[0][0] == "defer"
    assert calls2[1][0] == "followup"

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
    sent = asyncio.run(make_prefix_respond(message)(content="x", embed="E", view="V"))
    assert fake_message.sent[0]["content"] == "x"
    assert fake_message.sent[0]["embed"] == "E"
    assert fake_message.sent[0]["view"] == "V"
    assert isinstance(sent, FakeSentMessage)


def check_slash_dispatch_and_context():
    """The ``/`` detector must register 9 commands with a '/' context."""
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
    assert len(tree.commands) == 10, sorted(tree.commands)

    tree2 = FakeTree()
    detector = SlashDetector(bot="BOT")
    detector.setup("BOT", tree2)
    assert len(tree2.commands) == 10, sorted(tree2.commands)
    assert detector.bot == "BOT"

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

    ctx = build_slash_context(FakeInteraction(), args=["1", "100"])
    assert ctx.args == ["1", "100"]
    assert callable(ctx.respond)
