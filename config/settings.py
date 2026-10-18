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

# Optional Guild ID for instant slash command registration (instead of up to 1h Discord cache delay)
GUILD_ID = os.getenv("GUILD_ID")

# The now playing game. Set this to anything false-y ("", None) to disable it
NOW_PLAYING = COMMAND_PREFIX + "commands"

# Channel names — change these to match your Discord server's channel names
CHANNEL_BOT_ACTIVITY = "botactivity"
CHANNEL_DELETED       = "deleted"
CHANNEL_VOICE         = "voice"
CHANNEL_WAIFU         = "waifu"

# Base directory. Feel free to use it if you want.
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
