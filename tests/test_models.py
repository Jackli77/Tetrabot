"""Pure unit tests for the model layer (no I/O, no Discord, no database)."""
import random

from models import duels
from models.stats import Stats, winrate


def run():
    # --- winrate -----------------------------------------------------------
    assert winrate(0, 5) == 0      # no game played -> 0%
    assert winrate(3, 0) == 100    # only wins -> 100%
    assert winrate(1, 1) == 50
    assert winrate(1, 3) == 25
    assert winrate(10, 5) == 66

    # --- Stats helpers -----------------------------------------------------
    s = Stats(user_id=42, val=7, equity=-30, win=1, loss=3, username="alice")
    assert s.winrate == 25
    assert s.display_name == "alice"
    assert Stats(user_id=42).display_name == "42"  # falls back to the id
    assert Stats(user_id=42).winrate == 0

    # --- Gamble duels ------------------------------------------------------
    rng = random.Random(42)
    for upper in (3, 10, 100):
        rolls = duels.roll_gamble(upper, rng=rng)
        assert 1 <= rolls[0] <= upper + 1
        assert 1 <= rolls[1] <= upper + 1

    tie = duels.resolve_gamble(1, 2, 10, (5, 5))
    assert tie.is_tie and tie.diff == 0 and tie.winner_id is None and tie.loser_id is None

    r = duels.resolve_gamble(1, 2, 10, (9, 4))
    assert r.winner_id == 1 and r.loser_id == 2 and r.diff == 5
    assert r.decisive  # 5 >= 10 / 2

    r = duels.resolve_gamble(1, 2, 10, (3, 2))
    assert r.winner_id == 1 and r.diff == 1
    assert not r.decisive

    r = duels.resolve_gamble(1, 2, 10, (2, 7))
    assert r.winner_id == 2 and r.loser_id == 1 and r.diff == 5

    # --- Crit duels --------------------------------------------------------
    rng = random.Random(42)
    hits = sum(1 for _ in range(1000) if duels.crit_roll(15, rng=rng))
    assert 0 < hits < 1000  # sanity: 15% odds lands sometimes, not always
    assert all(not duels.crit_roll(0, rng=rng) for _ in range(50))    # 0% -> never
    assert all(duels.crit_roll(101, rng=rng) for _ in range(50))      # >100% -> always

    assert duels.escalate_stake(10, True) == 20   # both crit -> stake doubles
    assert duels.escalate_stake(10, False) == 10

    r = duels.resolve_crit(1, 2, 3, 1, 4, 40)
    assert r.winner_id == 1 and r.loser_id == 2 and r.ties == 1 and r.rounds == 4 and r.stake == 40
    r = duels.resolve_crit(1, 2, 0, 2, 3, 40)
    assert r.winner_id == 2 and r.loser_id == 1 and r.ties == 0

    print("test_models: all passed")
