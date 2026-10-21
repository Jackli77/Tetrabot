"""MODEL layer: data access and domain rules.

Models never import Discord UI, views, or command handlers.
"""
from tetrabot.models import context, db, duels, llm, memory, stats
from tetrabot.models.llm import ask
from tetrabot.models.memory import ConversationStore
from tetrabot.models.stats import Stats, get_stats, leaderboard, record_result, winrate

__all__ = [
    "Stats",
    "ask",
    "context",
    "db",
    "duels",
    "get_stats",
    "leaderboard",
    "llm",
    "memory",
    "record_result",
    "stats",
    "winrate",
    "ConversationStore",
]
