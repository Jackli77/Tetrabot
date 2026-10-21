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

#: How long the bot waits for the model, in seconds.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "180"))

#: How many times a request is retried when the server fails with a
#: temporary error (a 500 from a cloud backend, for instance).
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

#: How many tokens the model may generate.  Thinking models spend part of
#: this budget on their private reasoning, so the value must leave room for
#: the actual answer — too small and the model returns an empty reply.
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))

#: The token budget used when the first attempt came back empty.  The model
#: already consumed its reasoning budget, so the retry gets more room.
OLLAMA_RETRY_NUM_PREDICT = int(os.getenv("OLLAMA_RETRY_NUM_PREDICT", "8192"))

#: Sampling temperature.  Slightly lower than 1 keeps the answers on topic.
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

#: How much the model is allowed to think before answering:
#: "low", "medium", "high", or False to disable thinking entirely.
#: Thinking makes the answers better but slower, so "low" is the default.
#: Set it to "" (empty) to leave the decision to the model.
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "low") or False

#: How long the model stays loaded in memory.  Reloading it costs seconds,
#: so keeping it warm is what makes the bot feel snappy.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

#: Whether the answer is streamed into the channel as it is generated.
CHAT_STREAM = os.getenv("CHAT_STREAM", "1") not in ("0", "false", "False")

#: Minimum delay between two edits of the streamed message, in seconds.
#: Discord rate-limits message edits.
CHAT_EDIT_INTERVAL = float(os.getenv("CHAT_EDIT_INTERVAL", "1.2"))

#: How many conversations are remembered per channel.
CHAT_MEMORY_MESSAGES = int(os.getenv("CHAT_MEMORY_MESSAGES", "20"))

#: How long a conversation is kept, in seconds (default: 6 hours).
CHAT_MEMORY_TTL = float(os.getenv("CHAT_MEMORY_TTL", str(6 * 3600)))

#: The tools the chatbot may use to look things up.  Empty means "all of
#: them".  Available: get_weather, search_wikipedia, search_web, get_datetime.
CHAT_TOOLS = tuple(
    name.strip()
    for name in os.getenv(
        "CHAT_TOOLS", "get_weather,search_wikipedia,search_web,get_datetime"
    ).split(",")
    if name.strip()
)

#: How many tool rounds the model may run for a single question.  Each round
#: trip costs a full model call, so the loop is bounded.
CHAT_MAX_TOOL_ROUNDS = int(os.getenv("CHAT_MAX_TOOL_ROUNDS", "3"))

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
    "CHAT_EDIT_INTERVAL",
    "CHAT_MEMORY_MESSAGES",
    "CHAT_MEMORY_TTL",
    "CHAT_MAX_TOOL_ROUNDS",
    "CHAT_STREAM",
    "CHAT_TOOLS",
    "COMMAND_PREFIX",
    "MONGODB_URI",
    "NOW_PLAYING",
    "OLLAMA_HOST",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_MODEL",
    "OLLAMA_NUM_PREDICT",
    "OLLAMA_RETRIES",
    "OLLAMA_RETRY_NUM_PREDICT",
    "OLLAMA_TEMPERATURE",
    "OLLAMA_THINK",
    "OLLAMA_TIMEOUT",
]
