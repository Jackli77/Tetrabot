"""Tests for the command catalog — the single source of truth.

These lock down the invariants that keep the ``!`` router and the ``/`` tree
in sync: every catalog entry must point at a real implementation, and every
implementation must be reachable from a catalog entry.
"""
from __future__ import annotations

import asyncio

import discord
import pytest
from discord import app_commands

from tetrabot import catalog
from tetrabot.controllers.commands import HANDLERS
from tetrabot.controllers.slash import setup_slash_commands


class TestCatalogIntegrity:
    def test_every_command_points_at_a_real_implementation(self):
        for spec in catalog.COMMANDS:
            assert spec.handler in HANDLERS, f"{spec.name} -> {spec.handler} is missing"

    def test_every_implementation_is_reachable(self):
        used = {spec.handler for spec in catalog.COMMANDS}
        assert used == set(HANDLERS), f"unreachable: {set(HANDLERS) - used}"

    def test_the_chatbot_is_not_a_command(self):
        """The chatbot answers the listening channel: it is not a command."""
        spec = catalog.find("chat")
        assert spec is not None
        assert not spec.expose_as_prefix
        assert not spec.expose_as_slash
        assert "chat" not in [s.name for s in catalog.public_commands()]

    def test_the_public_commands_are_the_exposed_ones(self):
        for spec in catalog.public_commands():
            assert spec.expose_as_slash or spec.expose_as_prefix

    def test_command_names_are_unique(self):
        names = [spec.name for spec in catalog.COMMANDS]
        assert len(names) == len(set(names))

    def test_all_trigger_names_are_unique(self):
        triggers: list[str] = []
        for spec in catalog.COMMANDS:
            triggers.extend(spec.names)
        assert len(triggers) == len(set(triggers)), "duplicate trigger name"

    def test_slash_names_are_unique(self):
        names: list[str] = []
        for spec in catalog.slash_commands():
            names.extend(spec.slash_name_list)
        assert len(names) == len(set(names)), "duplicate slash command name"

    def test_every_command_has_a_description(self):
        for spec in catalog.COMMANDS:
            assert spec.description.strip(), spec.name

    def test_required_params_come_first(self):
        """A required parameter may never follow an optional one."""
        for spec in catalog.COMMANDS:
            flags = [p.required for p in spec.params]
            assert flags == sorted(flags, reverse=True), spec.name

    def test_only_the_duels_need_a_challenge(self):
        """The challenge flag is what tells the controller to host a duel."""
        needing = {spec.name for spec in catalog.COMMANDS if spec.needs_challenge}
        assert needing == {"gamble", "crit"}

    def test_every_command_with_a_challenge_is_a_duel(self):
        """A command that needs a challenge must be a guild-only command."""
        for spec in catalog.COMMANDS:
            if spec.needs_challenge:
                assert spec.scope.allows_guild, spec.name
                assert not spec.scope.allows_dm, spec.name


class TestLookup:
    def test_find_by_name(self):
        assert catalog.find("inc").name == "inc"

    def test_find_is_case_insensitive(self):
        assert catalog.find("INC").name == "inc"

    def test_find_by_alias(self):
        assert catalog.find("lb").name == "incscore"
        assert catalog.find("c").name == "clean"

    def test_find_unknown_returns_none(self):
        assert catalog.find("nope") is None


class TestScopes:
    def test_help_is_available_in_dm_and_guild(self):
        spec = catalog.find("commands")
        assert spec.scope.allows_guild
        assert spec.scope.allows_dm

    def test_duels_are_guild_only(self):
        for name in ("gamble", "crit"):
            spec = catalog.find(name)
            assert spec.scope.allows_guild
            assert not spec.scope.allows_dm

    def test_dm_commands_are_a_subset_of_the_catalog(self):
        for spec in catalog.dm_commands():
            assert spec in catalog.COMMANDS


class TestSlashTree:
    @pytest.fixture
    def tree(self):
        client = discord.Client(intents=discord.Intents.default())
        tree = app_commands.CommandTree(client)
        setup_slash_commands(client, tree)
        return tree

    def test_every_slash_command_is_registered(self, tree):
        registered = {command.name for command in tree.get_commands()}
        expected = {
            name
            for spec in catalog.slash_commands()
            for name in spec.slash_name_list
        }
        assert registered == expected

    def test_slash_options_match_the_catalog(self, tree):
        commands = {command.name: command for command in tree.get_commands()}
        gamble = commands["gamble"]
        assert [p.name for p in gamble.parameters] == ["limite"]
        assert gamble.parameters[0].required is True
        assert gamble.parameters[0].min_value == 1

    def test_optional_slash_options_have_defaults(self, tree):
        commands = {command.name: command for command in tree.get_commands()}
        random_cmd = commands["random"]
        by_name = {p.name: p for p in random_cmd.parameters}
        assert by_name["min"].required is False
        assert by_name["min"].default == 1
        assert by_name["max"].default == 100

    def test_option_descriptions_come_from_the_catalog(self, tree):
        commands = {command.name: command for command in tree.get_commands()}
        gamble = commands["gamble"]
        assert gamble.parameters[0].description == (
            "Somme maximale de la roulette (ex: 100)"
        )


class _FakeUser:
    def __init__(self, user_id=1, name="alice"):
        self.id = user_id
        self.name = name
        self.display_name = name
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.display_avatar = type("Avatar", (), {"url": "http://avatar"})()


class _FakeResponse:
    def __init__(self):
        self.calls = []
        self._done = False

    async def send_message(self, **kwargs):
        self.calls.append(("response", kwargs))
        self._done = True

    async def defer(self):
        self.calls.append(("defer", {}))
        self._done = True

    def is_done(self):
        return self._done


class _FakeFollowup:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def send(self, **kwargs):
        self.calls.append(("followup", kwargs))


class _FakeClient:
    def __init__(self):
        self.user = _FakeUser(0, "BOT")

    async def fetch_user(self, user_id):
        return _FakeUser(user_id)


class _FakeInteraction:
    def __init__(self):
        self.user = _FakeUser()
        self.channel = object()
        self.client = _FakeClient()
        self.response = _FakeResponse()
        self.followup = _FakeFollowup(self.response)


class TestSlashLeaderboard:
    """The ``/incscore`` command must answer the interaction exactly once."""

    @pytest.fixture
    def tree(self):
        client = discord.Client(intents=discord.Intents.default())
        tree = app_commands.CommandTree(client)
        setup_slash_commands(client, tree)
        return tree

    def test_responds_once_with_the_first_page(self, tree, monkeypatch):
        from tetrabot.models import stats as stats_mod

        from .conftest import FakeUsers

        fake = FakeUsers()
        fake.docs[1] = {
            "_id": 1, "val": 3, "equity": 42, "win": 2, "loss": 1, "username": "alice",
        }
        monkeypatch.setattr(stats_mod.db, "users", lambda: fake)

        command = {c.name: c for c in tree.get_commands()}["incscore"]
        interaction = _FakeInteraction()
        asyncio.run(command.callback(interaction))

        assert len(interaction.response.calls) == 1
        assert interaction.followup.calls == []
        kind, payload = interaction.response.calls[0]
        assert kind == "response"
        assert payload["embed"] is not None
        assert payload["view"] is not None
