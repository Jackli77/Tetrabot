"""Pure duel rules — no I/O, no Discord, fully unit-testable.

These functions decide who wins a gamble or crit duel and by how much; the
*storytelling* (messages, pacing) belongs to the command logic and the views.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class GambleResult:
    """Outcome of a two-dice gamble duel.

    ``winner_id``/``loser_id`` are ``None`` on a tie.  ``decisive`` is True
    when the gap is at least half of the upper bound (flavor wording change).
    """

    winner_id: int | None
    loser_id: int | None
    diff: int          # kakeras transferred (0 on a tie)
    rolled1: int
    rolled2: int
    upper: int

    @property
    def is_tie(self) -> bool:
        return self.winner_id is None

    @property
    def decisive(self) -> bool:
        return self.diff >= self.upper / 2


def roll_gamble(upper: int, rng=random) -> tuple[int, int]:
    """Roll both dice for a gamble (1 .. upper inclusive)."""
    return rng.randint(1, upper + 1), rng.randint(1, upper + 1)


def resolve_gamble(
    challenger_id: int,
    opponent_id: int,
    upper: int,
    rolls: tuple[int, int],
) -> GambleResult:
    """Decide a gamble duel from pre-rolled dice values."""
    rolled1, rolled2 = rolls
    if rolled1 == rolled2:
        return GambleResult(None, None, 0, rolled1, rolled2, upper)
    if rolled1 > rolled2:
        winner, loser = challenger_id, opponent_id
        diff = rolled1 - rolled2
    else:
        winner, loser = opponent_id, challenger_id
        diff = rolled2 - rolled1
    return GambleResult(winner, loser, diff, rolled1, rolled2, upper)


def crit_roll(odds: int, rng=random) -> bool:
    """True when a crit lands (``randint(0, 100) < odds``)."""
    return rng.randint(0, 100) < odds


def escalate_stake(stake: int, both_crit: bool) -> int:
    """The stake doubles when both players crit in the same round."""
    return stake * 2 if both_crit else stake


@dataclass
class CritDuelResult:
    """Final outcome of a crit duel (played until the crit counts diverge)."""

    winner_id: int
    loser_id: int
    rounds: int        # manches played
    ties: int          # min(crit1, crit2) — crits scored by both players
    crit1: int
    crit2: int
    stake: int         # final amount transferred


def resolve_crit(
    challenger_id: int,
    opponent_id: int,
    crit1: int,
    crit2: int,
    rounds: int,
    stake: int,
) -> CritDuelResult:
    """Decide a crit duel from the accumulated crit counts."""
    ties = min(crit1, crit2)
    if crit1 > crit2:
        return CritDuelResult(challenger_id, opponent_id, rounds, ties, crit1, crit2, stake)
    return CritDuelResult(opponent_id, challenger_id, rounds, ties, crit1, crit2, stake)


__all__ = [
    "CritDuelResult",
    "GambleResult",
    "crit_roll",
    "escalate_stake",
    "resolve_crit",
    "resolve_gamble",
    "roll_gamble",
]
