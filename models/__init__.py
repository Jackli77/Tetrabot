"""MODEL layer: data access and domain rules.

Models never import Discord UI, views, or controllers.
"""
from models import duels, ollama, stats
from models.ollama import ask_ollama
from models.stats import Stats, get_stats, leaderboard, record_result, winrate

__all__ = [
    "duels",
    "ollama",
    "stats",
    "ask_ollama",
    "Stats",
    "get_stats",
    "leaderboard",
    "record_result",
    "winrate",
]
