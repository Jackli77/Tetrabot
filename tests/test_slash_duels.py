"""Tests for the duel commands on the slash transport.

The regression these lock down: when the challenge is answered, the
interaction has *already* been used.  The next message of the duel must
therefore go through a follow-up — sending it as the first response raises
``InteractionResponded`` and the duel dies before showing anything or
touching the database.
"""
from __future__ import annotations

import asyncio

import discord
import pytest
from discord import app_commands

from tetrabot.controllers.slash import setup_slash_commands


class FakeResponse:
    """Mimics discord.py: one response, then ``InteractionResponded``."""

    def __init__(self):
        self.calls: list[tuple[str, object]] = []
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, content=None, **kwargs):
        if self._done:
            raise discord.errors.InteractionResponded("already responded")
        self.calls.append(("response", content))
        self._done = True

    async def defer(self, **kwargs):
        if self._done:
            raise discord.errors.InteractionResponded("already responded")
        self.calls.append(("defer", None))
        self._done = True

    async def edit_message(self, content=None, **kwargs):
        if self._done:
            raise discord.errors.InteractionResponded("already responded")
        self.calls.append(("edit", content))
        self._done = True


class FakeFollowup:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    async def send(self, content=None, **kwargs):
        self.calls.append(("followup", content))


class FakeUser:
    def __init__(self, user_id=1, name="alice"):
        self.id = user_id
        self.name = name
        self.display_name = name
        self.mention = f"<@{user_id}>"
        self.bot = False

    @property
    def display_avatar(self):
        return type("Avatar", (), {"url": "http://avatar"})()


class FakeClient:
    def __init__(self):
        self.user = FakeUser(0, "BOT")

    async def fetch_user(self, user_id):
        return FakeUser(user_id, "bob")


class FakeInteraction:
    def __init__(self):
        self.user = FakeUser(1, "alice")
        self.channel = object()
        self.client = FakeClient()
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeUsers:
    """An in-memory stand-in for the MongoDB ``users`` collection."""

    def __init__(self):
        self.docs: dict[int, dict] = {}

    async def update_one(self, flt, update, upsert=False, **kwargs):
        doc = self.docs.get(flt["_id"])
        if doc is None and upsert:
            doc = {"_id": flt["_id"]}
            doc.update(update.get("$setOnInsert", {}))
            self.docs[flt["_id"]] = doc

    async def find_one(self, flt, **kwargs):
        doc = self.docs.get(flt["_id"])
        return dict(doc) if doc else None

    async def find_one_and_update(self, flt, update, return_document=False, **kwargs):
        doc = self.docs[flt["_id"]]
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        return dict(doc)

    def find(self, *args, **kwargs):
        class Cursor:
            def __init__(self, docs):
                self._docs = docs

            def sort(self, field, direction=-1):
                self._docs = sorted(
                    self._docs, key=lambda d: d.get(field, 0), reverse=direction < 0
                )
                return self

            async def to_list(self, length=None):
                return self._docs if length is None else self._docs[:length]

        return Cursor(list(self.docs.values()))


@pytest.fixture
def tree():
    client = discord.Client(intents=discord.Intents.default())
    command_tree = app_commands.CommandTree(client)
    setup_slash_commands(client, command_tree)
    return command_tree


@pytest.fixture
def fake_users(monkeypatch):
    from tetrabot.models import stats as stats_mod

    users = FakeUsers()
    monkeypatch.setattr(stats_mod.db, "users", lambda: users)
    return users


@pytest.fixture
def no_sleep(monkeypatch):
    from tetrabot.controllers.commands import duels

    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr(duels, "sleep", _no_sleep)


@pytest.fixture
def accepted_challenge(monkeypatch):
    """Make the challenge button accept right away."""
    import tetrabot.views.widgets as widgets_mod

    original = widgets_mod.ChallengeView.__init__

    def patched_init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.accepted_by = FakeUser(2, "bob")
        self.stop()

    monkeypatch.setattr(widgets_mod.ChallengeView, "__init__", patched_init)


class TestSlashDuel:
    def test_the_duel_continues_after_the_challenge(
        self, tree, fake_users, no_sleep, accepted_challenge
    ):
        """The whole duel runs, even though the interaction was used.

        The challenge is the *first* answer of the interaction, so every
        message after it has to be a follow-up.
        """
        command = {c.name: c for c in tree.get_commands()}["gamble"]
        interaction = FakeInteraction()

        asyncio.run(command.callback(interaction, limite=10))

        # The duel showed its progress...
        assert len(interaction.followup.calls) >= 5, interaction.followup.calls
        joined = " ".join(str(call[1]) for call in interaction.followup.calls)
        assert "a tiré" in joined
        assert "score" in joined

        # ...and the database knows about both players.
        assert 1 in fake_users.docs
        assert 2 in fake_users.docs
        for uid in (1, 2):
            assert fake_users.docs[uid]["val"] == 1, fake_users.docs

    def test_the_challenge_is_the_first_response(
        self, tree, fake_users, no_sleep, accepted_challenge
    ):
        """The challenge itself is the interaction's first response."""
        command = {c.name: c for c in tree.get_commands()}["gamble"]
        interaction = FakeInteraction()

        asyncio.run(command.callback(interaction, limite=10))

        assert len(interaction.response.calls) == 1
        assert interaction.response.calls[0][0] == "response"

    def test_a_tie_still_updates_both_players(
        self, tree, fake_users, no_sleep, monkeypatch
    ):
        """A tied gamble ticks the games-played counter for both players."""
        from tetrabot.models import duels

        monkeypatch.setattr(duels, "roll_gamble", lambda upper: (5, 5))

        import tetrabot.views.widgets as widgets_mod

        original = widgets_mod.ChallengeView.__init__

        def patched_init(self, *args, **kwargs):
            original(self, *args, **kwargs)
            self.accepted_by = FakeUser(2, "bob")
            self.stop()

        monkeypatch.setattr(widgets_mod.ChallengeView, "__init__", patched_init)

        command = {c.name: c for c in tree.get_commands()}["gamble"]
        interaction = FakeInteraction()

        asyncio.run(command.callback(interaction, limite=10))

        for uid in (1, 2):
            assert fake_users.docs[uid]["val"] == 1, fake_users.docs
            assert fake_users.docs[uid]["equity"] == 0, fake_users.docs


class TestSlashResponder:
    """The responder must never raise on an already-answered interaction."""

    def test_it_falls_back_to_a_followup(self):
        from tetrabot.views.responders import SlashResponder

        interaction = FakeInteraction()
        # Somebody answered the interaction behind the responder's back.
        asyncio.run(interaction.response.send_message("already there"))

        responder = SlashResponder(interaction)
        asyncio.run(responder(content="after"))

        assert interaction.followup.calls == [("followup", "after")]

    def test_it_uses_the_response_first(self):
        from tetrabot.views.responders import SlashResponder

        interaction = FakeInteraction()
        responder = SlashResponder(interaction)
        asyncio.run(responder(content="first"))

        assert interaction.response.calls == [("response", "first")]
        assert interaction.followup.calls == []

    def test_the_second_message_is_a_followup(self):
        from tetrabot.views.responders import SlashResponder

        interaction = FakeInteraction()
        responder = SlashResponder(interaction)
        asyncio.run(responder(content="first"))
        asyncio.run(responder(content="second"))

        assert interaction.followup.calls == [("followup", "second")]
