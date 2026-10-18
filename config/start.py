"""CONFIG/start: bot factory — intents, client, detectors, slash tree.

``create_bot()`` builds a ready-to-run :class:`discord.ext.commands.Bot`:

* privileged ``message_content`` intent (enable it in the Developer Portal),
* the two detectors wired up:

  - :class:`detectors.prefix.PrefixDetector` handles ``!`` messages
    (``on_message`` / ``on_message_edit`` → ``handle_message``),
  - :class:`detectors.slash.SlashDetector` registers the native ``/`` tree,
* Discord lifecycle events:

  - ``on_ready`` → sync slash commands, announce readiness, init the DB,
    set the ``NOW_PLAYING`` status,
  - ``on_message_delete`` → log deleted content,
  - ``on_voice_state_update`` → announce voice joins/leaves.

Detectors only normalise transports into a shared
:class:`controllers.CommandContext`; the actual behaviour lives once in
``controllers.LOGIC``.
"""
import discord
from discord.ext import commands

from config import settings
from config.utils import get_channel
from detectors.prefix.detector import PrefixDetector, handle_message
from detectors.slash.detector import SlashDetector
from models import db as models_db


async def run_prefix_message(message, bot_client, detector: PrefixDetector | None = None):
    """Run an incoming message through the ``!`` detector, then dispatch.

    Thin wrapper around :func:`detectors.prefix.detector.handle_message`
    kept here so events stay one-liners and tests can import a stable entry
    point from ``config.start``.
    """
    return await handle_message(message, bot_client, detector=detector)


def create_bot() -> commands.Bot:
    """Build the bot client with every event handler attached."""
    intents = discord.Intents.default()
    intents.message_content = True

    print("Starting up...")
    bot_client = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

    # Detectors: one per invocation style, both feeding the same LOGIC.
    prefix_detector = PrefixDetector()
    slash_detector = SlashDetector()

    # Register Slash Commands into the bot tree via the / detector.
    slash_detector.setup(bot_client, bot_client.tree)

    # Track if on_ready has already executed to prevent double execution on reconnects
    has_started = False

    @bot_client.event
    async def on_ready():
        nonlocal has_started
        if has_started:
            return

        has_started = True
        print(f"Logged in as {bot_client.user} (ID: {bot_client.user.id})", flush=True)

        # Synchronize global slash commands with Discord
        # (note: global commands can take up to 1h to propagate on Discord's side)
        try:
            print("Syncing slash commands with Discord...", flush=True)
            synced = await bot_client.tree.sync()
            print(f"Synced {len(synced)} global slash commands successfully!", flush=True)
        except Exception as e:
            print(f"Failed to sync slash commands: {e}", flush=True)

        botactivity = get_channel(bot_client, settings.CHANNEL_BOT_ACTIVITY)
        if botactivity:
            await botactivity.send("Le bot est pret!")

        print("Verifying database integrity...", flush=True)
        await models_db.initialize(bot_client)

        # Set the playing status
        if settings.NOW_PLAYING:
            print("Setting NP game", flush=True)
            await bot_client.change_presence(
                activity=discord.Game(name=settings.NOW_PLAYING))
        print("Bot is ready and listening!", flush=True)

    @bot_client.event
    async def on_message(message):
        await run_prefix_message(message, bot_client, detector=prefix_detector)

    @bot_client.event
    async def on_message_edit(before, after):
        await run_prefix_message(after, bot_client, detector=prefix_detector)

    @bot_client.event
    async def on_message_delete(message):
        deleted = get_channel(bot_client, settings.CHANNEL_DELETED)
        if deleted:
            for i in message.embeds:
                await deleted.send(embed=i)
            if message.content:
                await deleted.send(
                    f"*{message.content}* écrit par **{message.author}** a été supprimé")
            else:
                await deleted.send(
                    f"*L'embed* écrit par **{message.author}** a été supprimé")

    @bot_client.event
    async def on_voice_state_update(member, before, after):
        voice = get_channel(bot_client, settings.CHANNEL_VOICE)
        if voice:
            if after.channel is None:
                await voice.send(f"**{member}** s'est déconnecté de **{before.channel}**")
            elif str(after.channel) != str(before.channel):
                await voice.send(f"**{member}** à rejoint le salon **{after.channel}**")

    return bot_client


def main():
    """Create the bot and connect it to Discord (blocking call)."""
    bot_client = create_bot()
    # Start the bot
    bot_client.run(settings.BOT_TOKEN)


__all__ = ["create_bot", "main", "run_prefix_message"]
