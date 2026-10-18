"""CONFIG layer: centralised settings and shared helpers.

Everything the bot needs to boot lives here:

* ``config.settings`` — environment variables (``.env``) and constants
  (command prefix, channel names, ...).
* ``config.utils`` — small Discord helpers shared by every layer
  (e.g. :func:`get_channel`).

Import either the submodule (``from config import settings``) or the
re-exported names (``from config import COMMAND_PREFIX``).
"""
from config.settings import (
    BASE_DIR,
    BOT_TOKEN,
    CHANNEL_BOT_ACTIVITY,
    CHANNEL_DELETED,
    CHANNEL_VOICE,
    CHANNEL_WAIFU,
    COMMAND_PREFIX,
    GUILD_ID,
    MONGODB_URI,
    NOW_PLAYING,
)
from config.utils import get_channel

__all__ = [
    "BASE_DIR",
    "BOT_TOKEN",
    "CHANNEL_BOT_ACTIVITY",
    "CHANNEL_DELETED",
    "CHANNEL_VOICE",
    "CHANNEL_WAIFU",
    "COMMAND_PREFIX",
    "GUILD_ID",
    "MONGODB_URI",
    "NOW_PLAYING",
    "get_channel",
]
