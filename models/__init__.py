"""MODEL layer: data access and domain rules.

Models never import Discord UI, views, or controllers.
"""
from models import duels, stats
from models.stats import Stats, get_stats, leaderboard, record_result, winrate

__all__ = [
    "duels",
    "stats",
    "Stats",
    "get_stats",
    "leaderboard",
    "record_result",
    "winrate",
]
