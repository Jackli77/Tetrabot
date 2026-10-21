"""Tests for the controllers — the ``!`` prefix transport and the ``/`` tree."""
from __future__ import annotations

import ast
import asyncio
import pathlib

import pytest

from tetrabot.controllers import BaseController, DetectionResult, PrefixController
from tetrabot.controllers.context import CommandContext
from tetrabot.controllers.prefix import handle_message
from tetrabot.views.responders import PrefixResponder, SlashResponder


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
    def controller(self):
        return PrefixController()

    def test_ignores_its_own_messages(self, controller):
        bot = FakeBot()
        result = asyncio.run(controller.detect(make_message("!inc", author=bot.user), bot))
        assert result.handled is False
        assert result.command is None

    def test_detects_a_dm(self, controller):
        bot = FakeBot()
        dm_channel = FakeChannel()
        message = make_message(
            "!commands", author=FakeAuthor(dm_channel=dm_channel), channel=dm_channel
        )
        result = asyncio.run(controller.detect(message, bot))
        assert result.handled is True
        assert result.is_dm is True
        assert result.command == "commands"
        assert result.args == []

    def test_detects_a_guild_command(self, controller):
        bot = FakeBot()
        result = asyncio.run(controller.detect(make_message("!GAMBLE 50"), bot))
        assert result.is_dm is False
        assert result.command == "gamble"
        assert result.args == ["50"]

    @pytest.mark.parametrize("content", ["hello", "!", ""])
    def test_ignores_non_commands(self, controller, content):
        bot = FakeBot()
        result = asyncio.run(controller.detect(make_message(content), bot))
        assert result.handled is False
        assert result.command is None

    def test_result_is_a_detection_result(self, controller):
        bot = FakeBot()
        result = asyncio.run(controller.detect(make_message("!inc"), bot))
        assert isinstance(result, DetectionResult)
        assert isinstance(controller, BaseController)
        assert controller.name == "!"


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

    def test_a_guild_only_command_is_refused_in_dm(self):
        """``!gamble`` is guild-only: in a DM it must stay completely silent."""
        bot = FakeBot()
        dm_channel = FakeChannel()
        message = make_message(
            "!gamble 10",
            author=FakeAuthor(dm_channel=dm_channel),
            channel=dm_channel,
        )
        asyncio.run(handle_message(message, bot))
        assert dm_channel.sent == []


class TestControllerPipeline:
    """The shared pipeline every transport follows."""

    def test_the_handler_runs_with_the_parsed_arguments(self, monkeypatch):
        """A dispatched command reaches its shared handler with the args."""
        from tetrabot.controllers import base

        seen = {}

        async def fake_handler(ctx):
            seen["args"] = list(ctx.args)
            seen["prefix"] = ctx.prefix

        monkeypatch.setitem(base.HANDLERS, "cmd_random", fake_handler)

        bot = FakeBot()
        channel = FakeChannel()
        message = make_message("!random 5 9", channel=channel)
        asyncio.run(handle_message(message, bot))

        assert seen["args"] == ["5", "9"]
        assert seen["prefix"] == "!"

    def test_an_unknown_handler_is_reported_not_raised(self, monkeypatch):
        """A catalog entry pointing at a missing handler must not crash."""
        from tetrabot import catalog
        from tetrabot.controllers import base

        monkeypatch.setitem(base.HANDLERS, "cmd_random", None)
        spec = catalog.find("random")
        assert spec is not None

        bot = FakeBot()
        channel = FakeChannel()
        message = make_message("!random", channel=channel)
        # Must not raise.
        asyncio.run(handle_message(message, bot))

    def test_the_controller_reports_the_missing_handler(self, monkeypatch, caplog):
        from tetrabot import catalog
        from tetrabot.controllers import base

        monkeypatch.setitem(base.HANDLERS, "cmd_random", None)
        spec = catalog.find("random")

        controller = PrefixController()
        with caplog.at_level("ERROR"):
            asyncio.run(controller.execute(spec, None))
        assert "cmd_random" in caplog.text


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


#: Which MVC layers each layer is allowed to depend on.  A layer may always
#: depend on itself.
ALLOWED_LAYERS = {
    "models": {"models", "config"},
    "views": {"views", "catalog"},
    "controllers": {"controllers", "models", "views", "catalog", "config"},
}

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "tetrabot"


def _is_type_checking(test) -> bool:
    """True for an ``if TYPE_CHECKING:`` guard."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _runtime_tetrabot_deps(path: pathlib.Path) -> set[str]:
    """The ``tetrabot`` modules a file imports at runtime.

    Imports guarded by ``if TYPE_CHECKING:`` are excluded: they are erased
    at runtime and cannot create a dependency.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    deps: set[str] = set()

    def visit(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking(child.test):
                continue  # type-only import -> no runtime dependency
            if isinstance(child, ast.ImportFrom):
                if child.level or not child.module:
                    continue
                if not child.module.startswith("tetrabot"):
                    continue
                if child.module == "tetrabot":
                    deps.update(f"tetrabot.{a.name}" for a in child.names)
                else:
                    deps.add(child.module)
            elif isinstance(child, ast.Import):
                deps.update(
                    a.name for a in child.names if a.name.startswith("tetrabot")
                )
            visit(child)

    visit(tree)
    return deps


class TestArchitecture:
    """The MVC layer boundaries must hold.

    A layer may only depend on the layers below it, so the Model and the
    View can never reach back into the Controller.
    """

    @pytest.mark.parametrize("layer", sorted(ALLOWED_LAYERS))
    def test_no_upward_imports(self, layer):
        violations = []
        for path in sorted((PACKAGE_ROOT / layer).rglob("*.py")):
            for dep in _runtime_tetrabot_deps(path):
                parts = dep.split(".")
                dep_layer = parts[1] if len(parts) > 1 else None
                if dep_layer and dep_layer not in ALLOWED_LAYERS[layer]:
                    violations.append(f"{path.name} imports {dep}")
        assert not violations, violations

    def test_the_three_layers_exist(self):
        assert (PACKAGE_ROOT / "models").is_dir()
        assert (PACKAGE_ROOT / "views").is_dir()
        assert (PACKAGE_ROOT / "controllers").is_dir()

    def test_the_model_never_imports_discord(self):
        """The Model layer stays free of any Discord dependency."""
        for path in sorted((PACKAGE_ROOT / "models").rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            assert "import discord" not in source, path

