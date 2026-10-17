"""VIEW layer: pure rendering (strings/embeds) plus Discord UI widgets.

Views only format data handed to them by controllers — they never query the
database and never contain command rules.
"""
from views import challenge, formatting, leaderboard
from views.challenge import CritChallengeView, GambleChallengeView
from views.formatting import (
    command_line,
    command_lines,
    render_aup_call,
    render_aup_urge,
    render_crit_escalation,
    render_crit_hit,
    render_crit_miss,
    render_crit_outcome,
    render_crit_round,
    render_gamble_intro,
    render_gamble_roll,
    render_gamble_tie,
    render_gamble_winner,
    render_help,
    render_leaderboard_pages,
    render_roulette,
    render_score,
    render_stats,
)
from views.leaderboard import LeaderboardPaginationView

__all__ = [
    "challenge",
    "formatting",
    "leaderboard",
    "CritChallengeView",
    "GambleChallengeView",
    "LeaderboardPaginationView",
    "command_line",
    "command_lines",
    "render_aup_call",
    "render_aup_urge",
    "render_crit_escalation",
    "render_crit_hit",
    "render_crit_miss",
    "render_crit_outcome",
    "render_crit_round",
    "render_gamble_intro",
    "render_gamble_roll",
    "render_gamble_tie",
    "render_gamble_winner",
    "render_help",
    "render_leaderboard_pages",
    "render_roulette",
    "render_score",
    "render_stats",
]
