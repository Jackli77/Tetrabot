"""CONFIG/start: bot factory — intents, client, events, slash tree.

``create_bot()`` builds a ready-to-run :class:`discord.ext.commands.Bot`:

* privileged ``message_content`` intent (enable it in the Developer Portal),
* slash commands registered on ``bot.tree``
  (see :mod:`controllers.slash`),
* Discord events wired to the :mod:`filters` pipeline and the shared
  :mod:`controllers` logic:

  - ``on_ready`` → sync slash commands, announce readiness, init the DB,
    set the ``NOW_PLAYING`` status,
  - ``on_message`` / ``on_message_edit`` → :func:`run_filters_message`,
  - ``on_message_delete`` → log deleted content,
  - ``on_voice_state_update`` → announce voice joins/leaves.
"""
import discord
from discord.ext import commands

from config import settings
from config.utils import get_channel
from controllers import slash as slash_commands
from filters import default_pipeline
from models import db as models_db


async def run_filters_message(message, bot_client):
    """Run an incoming message through the filters pipeline, then dispatch.

    Replaces the old inline ``common_handle_message``: every step (ignore
    self, DM vs guild routing, ``!`` parsing) is a composable filter.
    """
    result = await default_pipeline(prefix=settings.COMMAND_PREFIX).run(message, bot_client)
    if not result.proceed or result.command is None:
        return
    handler = result.handler
    if handler is None:
        from controllers.dm.router import handle_command as handle_dm_command
        from controllers.prefix.router import handle_command as handle_guild_command

        handler = handle_dm_command if result.extra.get("dm") else handle_guild_command
    try:
        await handler(result.command, result.args, message, bot_client)
    except Exception:
        print("Error while handling message", flush=True)
        raise


def create_bot() -> commands.Bot:
    """Build the bot client with every event handler attached."""
    intents = discord.Intents.default()
    intents.message_content = True

    print("Starting up...")
    bot_client = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

    # Register Slash Commands into the bot tree
    slash_commands.setup_slash_commands(bot_client, bot_client.tree)

    # Track if on_ready has already executed to prevent double execution on reconnects
    has_started = False

    @bot_client.event
    async def on_ready():
        nonlocal has_started
        if has_started:
            return

        has_started = True
        print(f"Logged in as {bot_client.user} (ID: {bot_client.user.id})", flush=True)

        # Synchronize slash commands with Discord
        try:
            print("Syncing slash commands with Discord...", flush=True)
            if settings.GUILD_ID:
                guild_obj = discord.Object(id=int(settings.GUILD_ID))
                bot_client.tree.copy_global_to(guild=guild_obj)
                synced_guild = await bot_client.tree.sync(guild=guild_obj)
                print(f"Synced {len(synced_guild)} slash commands instantly to Guild ID {settings.GUILD_ID}!", flush=True)

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
        await run_filters_message(message, bot_client)

    @bot_client.event
    async def on_message_edit(before, after):
        await run_filters_message(after, bot_client)

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


__all__ = ["create_bot", "main", "run_filters_message"]
