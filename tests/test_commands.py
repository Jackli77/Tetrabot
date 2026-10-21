"""Tests for the shared command logic.

These run the ``cmd_*`` functions against an in-memory stand-in for the
MongoDB ``users`` collection, so no Discord connection and no real database
are needed.  They lock down two regressions from the MVP refactor:

* ``cmd_gamble`` must persist equity for BOTH players (the loser's update
  used to be lost).
* A tied gamble must still tick the games-played counter for both players.
"""
from __future__ import annotations

import asyncio

import pytest

from tetrabot.commands import duels as duels_cmd
from tetrabot.commands import logic
from tetrabot.models import duels
from tetrabot.models import stats as stats_mod

from .conftest import FakeUser


@pytest.fixture
def patch_stats(monkeypatch, fake_users):
    """Point the stats model at the in-memory collection."""
    monkeypatch.setattr(stats_mod.db, "users", lambda: fake_users)
    return fake_users


@pytest.fixture
def no_sleep(monkeypatch):
    """Make the pacing delays instantaneous."""

    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr(logic, "sleep", _no_sleep)
    monkeypatch.setattr(duels_cmd, "sleep", _no_sleep)


class TestGamble:
    def test_persists_both_players(
        self, make_ctx, patch_stats, no_sleep, score_lines, monkeypatch
    ):
        """A decided gamble must move equity for the winner AND the loser."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["10"])
        # Deterministic rolls: challenger 9, opponent 4 -> challenger wins 5.
        monkeypatch.setattr(duels, "roll_gamble", lambda upper: (9, 4))

        async def challenge(request):
            return FakeUser(2, "bob")

        ctx.challenge = challenge

        asyncio.run(duels_cmd.cmd_gamble(ctx))

        alice, bob = patch_stats.docs[1], patch_stats.docs[2]
        assert (alice["val"], alice["equity"], alice["win"], alice["loss"]) == (1, 5, 1, 0)
        assert (bob["val"], bob["equity"], bob["win"], bob["loss"]) == (1, -5, 0, 1)
        # Both players get their score/equity line posted back in the channel.
        assert len(score_lines(responder)) == 2

    def test_tie_still_ticks_games_played(
        self, make_ctx, patch_stats, no_sleep, score_lines, monkeypatch
    ):
        """On a tie: no equity/win/loss change, but games played still ticks."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["10"])
        monkeypatch.setattr(duels, "roll_gamble", lambda upper: (5, 5))

        async def challenge(request):
            return FakeUser(2, "bob")

        ctx.challenge = challenge

        asyncio.run(duels_cmd.cmd_gamble(ctx))

        for uid in (1, 2):
            doc = patch_stats.docs[uid]
            assert doc["val"] == 1, doc
            assert doc["equity"] == 0, doc
            assert doc["win"] == 0 and doc["loss"] == 0, doc
        assert any(
            payload.get("content") and "égalité" in payload["content"]
            for payload in responder.sent
        )
        assert len(score_lines(responder)) == 2

    def test_without_an_opponent_nothing_is_persisted(
        self, make_ctx, patch_stats, no_sleep
    ):
        """A challenge nobody accepts must not touch the database."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["10"])
        # No challenge hook is installed, so nobody accepts.
        asyncio.run(duels_cmd.cmd_gamble(ctx))

        assert patch_stats.docs == {}
        assert any(
            payload.get("content") and "annulé" in payload["content"]
            for payload in responder.sent
        )

    def test_invalid_bound_is_rejected(self, make_ctx, patch_stats, no_sleep):
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["0"])
        asyncio.run(duels_cmd.cmd_gamble(ctx))
        assert patch_stats.docs == {}
        assert "strictement positif" in responder.sent[0]["content"]


class TestCrit:
    def test_persists_both_players(
        self, make_ctx, patch_stats, no_sleep, score_lines, monkeypatch
    ):
        """cmd_crit is the reference implementation: both sides are recorded."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["40"])
        # Round 1: challenger crits, opponent misses -> duel decided immediately.
        rolls = iter([True, False])
        monkeypatch.setattr(duels, "crit_roll", lambda odds: next(rolls))

        async def challenge(request):
            return FakeUser(2, "bob")

        ctx.challenge = challenge

        asyncio.run(duels_cmd.cmd_crit(ctx))

        alice, bob = patch_stats.docs[1], patch_stats.docs[2]
        assert (alice["val"], alice["equity"], alice["win"]) == (1, 40, 1)
        assert (bob["val"], bob["equity"], bob["loss"]) == (1, -40, 1)
        assert len(score_lines(responder)) == 2

    def test_out_of_range_odds_are_rejected(self, make_ctx, patch_stats, no_sleep):
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["40", "95"])
        asyncio.run(duels_cmd.cmd_crit(ctx))
        assert patch_stats.docs == {}
        assert "odds" in responder.sent[0]["content"]


class TestInc:
    def test_updates_the_database(self, make_ctx, patch_stats, score_lines):
        """!inc must create-or-update the caller's document (gain=0)."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"))
        asyncio.run(logic.cmd_inc(ctx))

        doc = patch_stats.docs[1]
        assert doc["val"] == 1, doc           # games played ticks
        assert doc["equity"] == 0, doc        # gain=0: equity untouched
        assert len(score_lines(responder)) == 1


class TestHelp:
    def test_sends_no_stats_writes(self, make_ctx, patch_stats):
        """cmd_help must only send the embed — no stray record_result calls."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"))
        asyncio.run(logic.cmd_help(ctx))

        assert patch_stats.docs == {}, patch_stats.docs
        assert len(responder.sent) == 1, responder.sent
        assert responder.sent[0].get("embed") is not None


class TestIncscore:
    def test_reports_an_empty_leaderboard(self, make_ctx, patch_stats):
        """With no players, the command says so instead of crashing."""
        ctx, responder = make_ctx(author=FakeUser(1, "alice"))
        asyncio.run(logic.cmd_incscore(ctx))
        assert "Aucun joueur" in responder.sent[0]["content"]

    def test_renders_the_pages(self, make_ctx, patch_stats):
        """The leaderboard is rendered into the transport's pagination."""
        patch_stats.docs[1] = {
            "_id": 1, "val": 3, "equity": 42, "win": 2, "loss": 1, "username": "alice",
        }
        ctx, responder = make_ctx(author=FakeUser(1, "alice"))
        seen = {}

        async def paginate(pages):
            seen["pages"] = pages

        ctx.paginate = paginate
        asyncio.run(logic.cmd_incscore(ctx))

        assert len(seen["pages"]) == 3
        assert seen["pages"][0].title == "🏆 Classement d'équité"


class TestRandom:
    def test_rejects_non_numeric_bounds(self, make_ctx):
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["abc"])
        asyncio.run(logic.cmd_random(ctx))
        assert "nombre" in responder.sent[0]["content"]

    def test_rejects_inverted_bounds(self, make_ctx):
        ctx, responder = make_ctx(author=FakeUser(1, "alice"), args=["10", "1"])
        asyncio.run(logic.cmd_random(ctx))
        assert "lower bound" in responder.sent[0]["content"]

