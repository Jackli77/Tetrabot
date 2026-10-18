"""Utility helper functions for Tetrabot."""

import discord


def get_channel(client: discord.Client, value: str, attribute: str = "name") -> discord.abc.GuildChannel | None:
    """Find a Discord channel by an attribute (name by default).

    Returns None with a warning log if not found.
    """
    channel = next(
        (c for c in client.get_all_channels() if getattr(c, attribute, "").lower() == value.lower()),
        None
    )
    if not channel:
        print(f"WARNING: channel '{value}' not found — check CHANNEL_* names in config/settings.py", flush=True)
    return channel
