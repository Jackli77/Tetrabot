import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# The prefix that will be used to parse commands.
# It doesn't have to be a single character!
COMMAND_PREFIX = "!"

# The bot token. Loaded from .env — keep that file secret!
BOT_TOKEN = os.getenv("BOT_TOKEN")

# MongoDB connection URI. Loaded from .env
MONGODB_URI = os.getenv("MONGODB_URI")

# Ollama local LLM configuration (loaded from .env).
# Base URL of the local Ollama server (default: http://localhost:11434).
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# The Ollama model used by the chat command (default: "qwen3:4b").
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
# How many recent channel messages to include as conversation context.
CHAT_CONTEXT_MESSAGES = int(os.getenv("CHAT_CONTEXT_MESSAGES", "10"))

# The now playing game. Set this to anything false-y ("", None) to disable it
NOW_PLAYING = COMMAND_PREFIX + "commands"

# Channel names — change these to match your Discord server's channel names
CHANNEL_BOT_ACTIVITY = "botactivity"
CHANNEL_DELETED       = "deleted"
CHANNEL_VOICE         = "voice"

# Base directory. Feel free to use it if you want.
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
