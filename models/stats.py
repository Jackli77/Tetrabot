"""MODEL: user statistics (score, equity, wins/losses) persisted in MongoDB."""
from __future__ import annotations

from dataclasses import dataclass

from models.db import users


@dataclass
class Stats:
    """A user's persisted stats document."""

    user_id: int
    val: int = 0        # games played (score counter)
    equity: int = 0     # net kakeras won/lost
    win: int = 0
    loss: int = 0
    username: str = ""

    @property
    def winrate(self) -> int:
        """Win percentage, 0 when no game was played."""
        return winrate(self.win, self.loss)

    @property
    def display_name(self) -> str:
        """Username stored in the DB, falling back to the raw user id."""
        return self.username or str(self.user_id)


def winrate(win: int, loss: int) -> int:
    """Calculate win percentage from wins and losses. Returns 0 if no games played."""
    if win == 0:
        return 0
    return 100 * win // (win + loss)


def _to_stats(doc: dict) -> Stats:
    """Convert a raw MongoDB document into a :class:`Stats`."""
    return Stats(
        user_id=doc["_id"],
        val=doc.get("val", 0),
        equity=doc.get("equity", 0),
        win=doc.get("win", 0),
        loss=doc.get("loss", 0),
        username=doc.get("username", ""),
    )


async def get_stats(user_id: int) -> Stats:
    """Fetch a user's stats, creating the document with defaults if missing.

    Delegates to :func:`record_result` with ``gain=0`` (no equity/win/loss
    change — but the games-played counter still ticks, as it always has).
    """
    return await record_result(user_id, 0)


async def record_result(user_id: int, gain: int) -> Stats:
    """Upsert a user record, apply ``gain`` to equity, and count a win or loss.

    Returns the updated stats.
    """
    # Ensure the user document exists; create with defaults if it doesn't.
    await users.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"val": 0, "equity": 0, "win": 0, "loss": 0}},
        upsert=True,
    )

    # Build the $inc payload: always increment total games played and equity.
    inc_fields = {"val": 1, "equity": gain}
    # Record a win or loss depending on whether gain is positive or negative.
    if gain < 0:
        inc_fields["loss"] = 1
    elif gain > 0:
        inc_fields["win"] = 1

    doc = await users.find_one_and_update(
        {"_id": user_id},
        {"$inc": inc_fields},
        return_document=True,  # Return the document AFTER the update
    )
    return _to_stats(doc)


async def leaderboard() -> list[Stats]:
    """All users sorted by equity (best first)."""
    docs = await users.find().sort("equity", -1).to_list(length=None)
    return [_to_stats(doc) for doc in docs]
