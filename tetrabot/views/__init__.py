"""VIEW layer: pure rendering, Discord UI widgets and output adapters.

``formatting`` turns data into strings and embeds; ``widgets`` holds the
interactive ``discord.ui`` views; ``responders`` adapts a Discord message
or interaction to one tiny output interface.  None of them query the
database or contain command rules.
"""
from tetrabot.views import chat, formatting, responders, widgets
from tetrabot.views.chat import (
    render_chat_embed,
    render_chat_error,
    render_chat_stream,
    render_chat_thinking,
)
from tetrabot.views.formatting import (
    render_aup_call,
    render_aup_urge,
    render_challenge_embed,
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
    render_missing_arguments,
    render_roulette,
    render_score,
    render_stats,
)
from tetrabot.views.responders import PrefixResponder, Responder, SlashResponder
from tetrabot.views.widgets import ChallengeView, LeaderboardPaginationView

__all__ = [
    "ChallengeView",
    "LeaderboardPaginationView",
    "PrefixResponder",
    "Responder",
    "SlashResponder",
    "chat",
    "formatting",
    "render_aup_call",
    "render_aup_urge",
    "render_challenge_embed",
    "render_chat_embed",
    "render_chat_error",
    "render_chat_stream",
    "render_chat_thinking",
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
    "render_missing_arguments",
    "render_roulette",
    "render_score",
    "render_stats",
    "responders",
    "widgets",
]
