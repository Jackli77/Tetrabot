"""The bot factory: intents, client, detectors, slash tree and event handlers.

:func:`create_bot` builds a ready-to-run :class:`discord.ext.commands.Bot`:

* privileged ``message_content`` intent (enable it in the Developer Portal),
* the two detectors wired up:

  - :class:`tetrabot.detectors.prefix.PrefixDetector` handles ``!`` messages
    (``on_message`` / ``on_message_edit`` → ``handle_message``),
  - :class:`tetrabot.detectors.slash.SlashDetector` registers the ``/`` tree,
* Discord lifecycle events:

  - ``on_ready`` → sync slash commands, announce readiness, init the DB,
    set the ``NOW_PLAYING`` status,
  - ``on_message_delete`` → log deleted content,
  - ``on_voice_state_update`` → announce voice joins/leaves.

Detectors only normalise transports into a shared
:class:`tetrabot.context.CommandContext`; the actual behaviour lives once in
:mod:`tetrabot.commands`.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from tetrabot import config
from tetrabot.detectors.prefix import PrefixDetector, handle_message
from tetrabot.detectors.slash import SlashDetector
from tetrabot.helpers import find_channel
from tetrabot.models import db

logger = logging.getLogger(__name__)


async def run_prefix_message(message, bot_client, detector: PrefixDetector | None = None):
    """Run an incoming message through the ``!`` detector, then dispatch.

    Thin wrapper around :func:`tetrabot.detectors.prefix.handle_message`
    kept here so events stay one-liners and tests can import a stable entry
    point from ``tetrabot.app``.
    """
    return await handle_message(message, bot_client, detector=detector)


def create_bot() -> commands.Bot:
    """Build the bot client with every event handler attached."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot_client = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)

    # Detectors: one per invocation style, both feeding the same logic.
    prefix_detector = PrefixDetector()
    slash_detector = SlashDetector()

    # Register the slash commands into the bot tree via the / detector.
    slash_detector.setup(bot_client, bot_client.tree)

    # Track if on_ready has already executed to prevent double execution on reconnects
    has_started = False

    @bot_client.event
    async def on_ready():
        nonlocal has_started
        if has_started:
            return

        has_started = True
        logger.info("Logged in as %s (ID: %s)", bot_client.user, bot_client.user.id)

        # Synchronize global slash commands with Discord
        # (note: global commands can take up to 1h to propagate on Discord's side)
        try:
            logger.info("Syncing slash commands with Discord...")
            synced = await bot_client.tree.sync()
            logger.info("Synced %d global slash commands successfully!", len(synced))
        except Exception:
            logger.exception("Failed to sync slash commands")

        botactivity = find_channel(bot_client, config.CHANNEL_BOT_ACTIVITY)
        if botactivity:
            await botactivity.send("Le bot est pret!")

        logger.info("Verifying database integrity...")
        await db.initialize(bot_client)

        # Set the playing status
        if config.NOW_PLAYING:
            logger.info("Setting NP game")
            await bot_client.change_presence(
                activity=discord.Game(name=config.NOW_PLAYING))
        logger.info("Bot is ready and listening!")

    @bot_client.event
    async def on_message(message):
        await run_prefix_message(message, bot_client, detector=prefix_detector)

    @bot_client.event
    async def on_message_edit(before, after):
        await run_prefix_message(after, bot_client, detector=prefix_detector)

    @bot_client.event
    async def on_message_delete(message):
        deleted = find_channel(bot_client, config.CHANNEL_DELETED)
        if deleted:
            for embed in message.embeds:
                await deleted.send(embed=embed)
            if message.content:
                await deleted.send(
                    f"*{message.content}* écrit par **{message.author}** a été supprimé")
            else:
                await deleted.send(
                    f"*L'embed* écrit par **{message.author}** a été supprimé")

    @bot_client.event
    async def on_voice_state_update(member, before, after):
        voice = find_channel(bot_client, config.CHANNEL_VOICE)
        if voice:
            if after.channel is None:
                await voice.send(f"**{member}** s'est déconnecté de **{before.channel}**")
            elif str(after.channel) != str(before.channel):
                await voice.send(f"**{member}** à rejoint le salon **{after.channel}**")

    return bot_client


def main() -> None:
    """Create the bot and connect it to Discord (blocking call)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
    )
    if not config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not set — copy .env.example to .env and fill it in."
        )

    bot_client = create_bot()
    bot_client.run(config.BOT_TOKEN)


__all__ = ["create_bot", "main", "run_prefix_message"]
