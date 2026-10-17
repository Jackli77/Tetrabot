"""Controller tests: gamble/crit/inc stats really hit the database.

These run the ``cmd_*`` controllers against an in-memory stand-in for the
MongoDB ``users`` collection, so no Discord connection and no real database
are needed.  They lock down two regressions from the MVP refactor:

* ``cmd_gamble`` must persist equity for BOTH players (the loser's update
  used to be lost), and ``cmd_help`` must not contain stray
  ``record_result`` calls (they raised NameError).
* A tied gamble must still tick the games-played counter for both players,
  exactly like the pre-refactor ``incdb`` helper did.
"""
import asyncio
import contextlib

from controllers import LOGIC, CommandContext
import controllers.commands as cc
from models import stats as stats_mod


class _FakeUsers:
    """Minimal async stand-in for the MongoDB ``users`` collection."""

    def __init__(self):
        self.docs = {}

    async def update_one(self, flt, update, upsert=False, **kwargs):
        # Only the $setOnInsert branch is needed: record_result upserts
        # defaults first, then applies the $inc payload.
        doc = self.docs.get(flt["_id"])
        if doc is None and upsert:
            doc = {"_id": flt["_id"]}
            doc.update(update.get("$setOnInsert", {}))
            self.docs[flt["_id"]] = doc

    async def find_one_and_update(self, flt, update, return_document=False, **kwargs):
        doc = self.docs[flt["_id"]]
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        return dict(doc)


class _FakeUser:
    def __init__(self, user_id, name):
        self.id = user_id
        self.display_name = name
        self.mention = f"<@{user_id}>"


class _FakeClient:
    async def fetch_user(self, user_id):
        return _FakeUser(user_id, "alice")


async def _no_sleep(_delay):
    return None


@contextlib.contextmanager
def _patched(fake_users, *patches):
    """Install a fake ``users`` collection, a no-op ``sleep``, and patches.

    ``patches`` are ``(obj, attr, replacement)`` triples.  Everything is
    restored on exit, even if the test raises.
    """
    replacements = [
        (stats_mod, "users", fake_users),
        (cc, "sleep", _no_sleep),
    ] + list(patches)
    originals = [(obj, name, getattr(obj, name)) for obj, name, _ in replacements]
    for obj, name, value in replacements:
        setattr(obj, name, value)
    try:
        yield
    finally:
        for obj, name, value in originals:
            setattr(obj, name, value)


def _make_ctx(sent, author=None, client=None):
    """Build a CommandContext whose respond() records every payload."""

    async def respond(**kwargs):
        sent.append(kwargs)

    return CommandContext(
        author=author or _FakeUser(1, "alice"),
        channel=None,
        client=client,
        args=[],
        respond=respond,
        prefix="!",
    )


def _score_lines(sent):
    return [m["content"] for m in sent if m.get("content") and "équité" in m["content"]]


def check_gamble_persists_both_players():
    """A decided gamble must move equity for the winner AND the loser."""
    fake = _FakeUsers()
    sent = []
    ctx = _make_ctx(sent, author=_FakeUser(1, "alice"))
    # Deterministic rolls: challenger 9, opponent 4 -> challenger wins 5.
    with _patched(fake, (cc.duels, "roll_gamble", lambda upper: (9, 4))):
        asyncio.run(cc.cmd_gamble(ctx, _FakeUser(2, "bob"), 10))

    alice, bob = fake.docs[1], fake.docs[2]
    assert (alice["val"], alice["equity"], alice["win"], alice["loss"]) == (1, 5, 1, 0)
    assert (bob["val"], bob["equity"], bob["win"], bob["loss"]) == (1, -5, 0, 1)
    # Both players get their score/equity line posted back in the channel.
    assert len(_score_lines(sent)) == 2, sent


def check_gamble_tie_still_ticks_games_played():
    """On a tie: no equity/win/loss change, but games played still ticks."""
    fake = _FakeUsers()
    sent = []
    ctx = _make_ctx(sent, author=_FakeUser(1, "alice"))
    with _patched(fake, (cc.duels, "roll_gamble", lambda upper: (5, 5))):
        asyncio.run(cc.cmd_gamble(ctx, _FakeUser(2, "bob"), 10))

    for uid in (1, 2):
        doc = fake.docs[uid]
        assert doc["val"] == 1, doc
        assert doc["equity"] == 0, doc
        assert doc["win"] == 0 and doc["loss"] == 0, doc
    assert any(m.get("content") and "égalité" in m["content"] for m in sent), sent
    assert len(_score_lines(sent)) == 2, sent


def check_crit_persists_both_players():
    """cmd_crit is the reference implementation: both sides are recorded."""
    fake = _FakeUsers()
    sent = []
    ctx = _make_ctx(sent, author=_FakeUser(1, "alice"))
    # Round 1: challenger crits, opponent misses -> duel decided immediately.
    rolls = iter([True, False])
    with _patched(fake, (cc.duels, "crit_roll", lambda odds: next(rolls))):
        asyncio.run(cc.cmd_crit(ctx, _FakeUser(2, "bob"), 40, 15))

    alice, bob = fake.docs[1], fake.docs[2]
    assert (alice["val"], alice["equity"], alice["win"]) == (1, 40, 1)
    assert (bob["val"], bob["equity"], bob["loss"]) == (1, -40, 1)
    assert len(_score_lines(sent)) == 2, sent


def check_inc_updates_the_database():
    """!inc must create-or-update the caller's document (gain=0)."""
    fake = _FakeUsers()
    sent = []
    ctx = _make_ctx(sent, author=_FakeUser(1, "alice"), client=_FakeClient())
    with _patched(fake):
        asyncio.run(cc.cmd_inc(ctx))

    doc = fake.docs[1]
    assert doc["val"] == 1, doc           # games played ticks
    assert doc["equity"] == 0, doc        # gain=0: equity untouched
    assert len(_score_lines(sent)) == 1, sent


def check_help_sends_no_stats_writes():
    """cmd_help must only send the embed — no stray record_result calls."""
    fake = _FakeUsers()
    sent = []
    ctx = _make_ctx(sent, author=_FakeUser(1, "alice"))
    with _patched(fake):
        asyncio.run(LOGIC["cmd_help"](ctx))

    assert fake.docs == {}, fake.docs     # help never writes stats
    assert len(sent) == 1, sent           # exactly one respond: the help embed
    assert sent[0].get("embed") is not None, sent


def run():
    check_gamble_persists_both_players()
    check_gamble_tie_still_ticks_games_played()
    check_crit_persists_both_players()
    check_inc_updates_the_database()
    check_help_sends_no_stats_writes()
    print("test_db_updates: all passed")
