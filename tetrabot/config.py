"""Application settings — every environment-driven value in one place.

Nothing else in the codebase reads ``os.environ`` directly: modules import
this module and use the constants below.  Values that are secrets come from
the ``.env`` file (see ``.env.example``); the rest are plain constants that
can be tweaked for your own Discord server.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the .env file (if present).
load_dotenv()

#: Root of the repository — handy to resolve data files.
BASE_DIR = Path(__file__).resolve().parent.parent

#: The prefix used to parse ``!`` commands. It doesn't have to be a single
#: character.
COMMAND_PREFIX = "!"

#: The Discord bot token. Loaded from .env — keep that file secret!
BOT_TOKEN = os.getenv("BOT_TOKEN")

#: MongoDB connection URI. Loaded from .env.
MONGODB_URI = os.getenv("MONGODB_URI")

#: Base URL of the local Ollama server (default: http://localhost:11434).
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

#: The Ollama model used by the chat command (default: "qwen3:4b").
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")

#: How many recent channel messages to include as conversation context.
CHAT_CONTEXT_MESSAGES = int(os.getenv("CHAT_CONTEXT_MESSAGES", "10"))

#: The now playing game. Set this to anything false-y ("", None) to disable it.
NOW_PLAYING = COMMAND_PREFIX + "commands"

#: Channel names — change these to match your Discord server's channel names.
CHANNEL_BOT_ACTIVITY = "botactivity"
CHANNEL_DELETED = "deleted"
CHANNEL_VOICE = "voice"


__all__ = [
    "BASE_DIR",
    "BOT_TOKEN",
    "CHANNEL_BOT_ACTIVITY",
    "CHANNEL_DELETED",
    "CHANNEL_VOICE",
    "CHAT_CONTEXT_MESSAGES",
    "COMMAND_PREFIX",
    "MONGODB_URI",
    "NOW_PLAYING",
    "OLLAMA_HOST",
    "OLLAMA_MODEL",
]
