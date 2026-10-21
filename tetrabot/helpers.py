"""Small Discord helpers shared by the whole bot."""
from __future__ import annotations

import logging

import discord

logger = logging.getLogger(__name__)


def find_channel(
    client: discord.Client,
    value: str,
    attribute: str = "name",
) -> discord.abc.GuildChannel | None:
    """Find a Discord channel by an attribute (name by default).

    Returns None with a warning log if not found.
    """
    channel = next(
        (c for c in client.get_all_channels() if getattr(c, attribute, "").lower() == value.lower()),
        None
    )
    if not channel:
        logger.warning(
            "channel '%s' not found — check the CHANNEL_* names in tetrabot/config.py",
            value,
        )
    return channel


__all__ = ["find_channel"]
