"""VIEW layer: pure rendering plus Discord UI widgets.

``formatting`` turns data into strings and embeds; ``widgets`` holds the
interactive ``discord.ui`` views.  Neither of them queries the database or
contains command rules.
"""
from tetrabot.views import formatting, widgets
from tetrabot.views.formatting import (
    render_aup_call,
    render_aup_urge,
    render_chat,
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
from tetrabot.views.widgets import ChallengeView, LeaderboardPaginationView

__all__ = [
    "ChallengeView",
    "LeaderboardPaginationView",
    "formatting",
    "render_aup_call",
    "render_aup_urge",
    "render_chat",
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
    "widgets",
]
