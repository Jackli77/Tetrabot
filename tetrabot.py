import sys
import discord
from discord.ext import commands

import settings
import database_init
import message_handler
import dms_handler
import slash_commands
from utils import get_channel


###############################################################################

def main():
    # Enable the intents the bot needs
    # NOTE: message_content is a Privileged Intent — enable it at:
    # https://discord.com/developers/applications/ → Bot → Privileged Gateway Intents
    intents = discord.Intents.default()
    intents.message_content = True

    # Initialize the commands.Bot client (supports both prefix commands & slash commands)
    print("Starting up...")
    client = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

    # Register Slash Commands into the bot tree
    slash_commands.setup_slash_commands(client, client.tree)

    # Track if on_ready has already executed to prevent double execution on reconnects
    has_started = False

    # Define event handlers for the client
    @client.event
    async def on_ready():
        nonlocal has_started
        if has_started:
            return

        has_started = True
        print(f"Logged in as {client.user} (ID: {client.user.id})", flush=True)

        # Synchronize slash commands with Discord
        try:
            print("Syncing slash commands with Discord...", flush=True)
            if settings.GUILD_ID:
                guild_obj = discord.Object(id=int(settings.GUILD_ID))
                client.tree.copy_global_to(guild=guild_obj)
                synced_guild = await client.tree.sync(guild=guild_obj)
                print(f"Synced {len(synced_guild)} slash commands instantly to Guild ID {settings.GUILD_ID}!", flush=True)

            synced = await client.tree.sync()
            print(f"Synced {len(synced)} global slash commands successfully!", flush=True)
        except Exception as e:
            print(f"Failed to sync slash commands: {e}", flush=True)

        botactivity = get_channel(client, settings.CHANNEL_BOT_ACTIVITY)
        if botactivity:
            await botactivity.send("Le bot est pret!")

        print("Verifying database integrity...", flush=True)
        await database_init.initialize(client)

        # Set the playing status
        if settings.NOW_PLAYING:
            print("Setting NP game", flush=True)
            await client.change_presence(
                activity=discord.Game(name=settings.NOW_PLAYING))
        print("Bot is ready and listening!", flush=True)

    # The message handler for both new messages and edits
    async def common_handle_message(message):
        # Ignore messages from the bot itself
        if message.author == client.user:
            return

        text = message.content
        if message.channel == message.author.dm_channel:
            handler = dms_handler.handle_command
            await message.author.send("received")
        else:
            handler = message_handler.handle_command

        if text.startswith(settings.COMMAND_PREFIX) and text != settings.COMMAND_PREFIX:
            cmd_split = text[len(settings.COMMAND_PREFIX):].split()
            try:
                await handler(cmd_split[0].lower(), cmd_split[1:], message, client)
            except Exception:
                print("Error while handling message", flush=True)
                raise

    @client.event
    async def on_message(message):
        await common_handle_message(message)

    @client.event
    async def on_message_edit(before, after):
        await common_handle_message(after)

    @client.event
    async def on_message_delete(message):
        deleted = get_channel(client, settings.CHANNEL_DELETED)
        if deleted:
            for i in message.embeds:
                await deleted.send(embed=i)
            if message.content:
                await deleted.send(
                    f"*{message.content}* écrit par **{message.author}** a été supprimé")
            else:
                await deleted.send(
                    f"*L'embed* écrit par **{message.author}** a été supprimé")

    @client.event
    async def on_voice_state_update(member, before, after):
        voice = get_channel(client, settings.CHANNEL_VOICE)
        if voice:
            if after.channel is None:
                await voice.send(f"**{member}** s'est déconnecté de **{before.channel}**")
            elif str(after.channel) != str(before.channel):
                await voice.send(f"**{member}** à rejoint le salon **{after.channel}**")

    # Start the bot
    client.run(settings.BOT_TOKEN)


###############################################################################

if __name__ == "__main__":
    main()
