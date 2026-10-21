"""MODEL layer: data access and domain rules.

Models never import Discord UI, views, or command logic.
"""
from tetrabot.models import db, duels, llm, stats
from tetrabot.models.llm import ask
from tetrabot.models.stats import Stats, get_stats, leaderboard, record_result, winrate

__all__ = [
    "Stats",
    "ask",
    "db",
    "duels",
    "get_stats",
    "leaderboard",
    "llm",
    "record_result",
    "stats",
    "winrate",
]
