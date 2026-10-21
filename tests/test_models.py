"""Pure unit tests for the model layer (no I/O, no Discord, no database)."""
from __future__ import annotations

import random

from tetrabot.models import duels
from tetrabot.models.stats import Stats, winrate


class TestWinrate:
    def test_no_game_played(self):
        assert winrate(0, 5) == 0

    def test_only_wins(self):
        assert winrate(3, 0) == 100

    def test_even_split(self):
        assert winrate(1, 1) == 50

    def test_rounded_down(self):
        assert winrate(1, 3) == 25
        assert winrate(10, 5) == 66


class TestStats:
    def test_winrate_property(self):
        assert Stats(user_id=42, win=1, loss=3).winrate == 25

    def test_display_name_prefers_username(self):
        assert Stats(user_id=42, username="alice").display_name == "alice"

    def test_display_name_falls_back_to_id(self):
        assert Stats(user_id=42).display_name == "42"

    def test_winrate_is_zero_without_games(self):
        assert Stats(user_id=42).winrate == 0


class TestGambleDuels:
    def test_rolls_stay_in_range(self):
        rng = random.Random(42)
        for upper in (3, 10, 100):
            rolls = duels.roll_gamble(upper, rng=rng)
            assert 1 <= rolls[0] <= upper + 1
            assert 1 <= rolls[1] <= upper + 1

    def test_tie(self):
        result = duels.resolve_gamble(1, 2, 10, (5, 5))
        assert result.is_tie
        assert result.diff == 0
        assert result.winner_id is None
        assert result.loser_id is None

    def test_challenger_wins(self):
        result = duels.resolve_gamble(1, 2, 10, (9, 4))
        assert result.winner_id == 1
        assert result.loser_id == 2
        assert result.diff == 5
        assert result.decisive

    def test_close_win_is_not_decisive(self):
        result = duels.resolve_gamble(1, 2, 10, (3, 2))
        assert result.winner_id == 1
        assert result.diff == 1
        assert not result.decisive

    def test_opponent_wins(self):
        result = duels.resolve_gamble(1, 2, 10, (2, 7))
        assert result.winner_id == 2
        assert result.loser_id == 1
        assert result.diff == 5


class TestCritDuels:
    def test_crit_lands_sometimes(self):
        rng = random.Random(42)
        hits = sum(1 for _ in range(1000) if duels.crit_roll(15, rng=rng))
        assert 0 < hits < 1000

    def test_zero_percent_never_crits(self):
        rng = random.Random(1)
        assert all(not duels.crit_roll(0, rng=rng) for _ in range(50))

    def test_above_hundred_always_crits(self):
        rng = random.Random(1)
        assert all(duels.crit_roll(101, rng=rng) for _ in range(50))

    def test_stake_doubles_when_both_crit(self):
        assert duels.escalate_stake(10, True) == 20
        assert duels.escalate_stake(10, False) == 10

    def test_challenger_wins_the_crit_duel(self):
        result = duels.resolve_crit(1, 2, 3, 1, 4, 40)
        assert result.winner_id == 1
        assert result.loser_id == 2
        assert result.ties == 1
        assert result.rounds == 4
        assert result.stake == 40

    def test_opponent_wins_the_crit_duel(self):
        result = duels.resolve_crit(1, 2, 0, 2, 3, 40)
        assert result.winner_id == 2
        assert result.loser_id == 1
        assert result.ties == 0
