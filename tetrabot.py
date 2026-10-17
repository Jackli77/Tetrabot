import sys
import settings
import discord
import message_handler
import dms_handler
import database_init
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from events.base_event import BaseEvent
from cronevents.base_cronevent import BaseCronEvent
from cronevents import *
from events import *

from utils import get_channel

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

# Scheduler that will be used to manage events
sched = AsyncIOScheduler()


###############################################################################

def main():
    # Enable the intents the bot needs
    # NOTE: message_content is a Privileged Intent — enable it at:
    # https://discord.com/developers/applications/ → Bot → Privileged Gateway Intents
    intents = discord.Intents.default()
    intents.message_content = True

    # Initialize the client
    print("Starting up...")
    client = discord.Client(intents=intents)

    # Define event handlers for the client
    # on_ready may be called multiple times in the event of a reconnect,
    # hence the running flag
    @client.event
    async def on_ready():
        if this.running:
            return

        this.running = True
        print(f"Logged in as {client.user} (ID: {client.user.id})", flush=True)

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

        # Load all interval events
        print("Loading events...", flush=True)
        n_ev = 0
        for ev in BaseEvent.__subclasses__():
            event = ev()
            sched.add_job(event.run, 'interval', (client,),
                          minutes=event.interval_minutes)
            n_ev += 1

        for crev in BaseCronEvent.__subclasses__():
            cronevent = crev()
            sched.add_job(cronevent.run, 'cron', (client,),
                          year=cronevent.year, month=cronevent.month, day=cronevent.day,
                          week=cronevent.week, day_of_week=cronevent.day_of_week,
                          hour=cronevent.hour, minute=cronevent.minute,
                          second=cronevent.second)
            n_ev += 1

        sched.start()
        print(f"{n_ev} events loaded", flush=True)

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

    async def createMutedRole(message):
        mutedRole = await message.guild.create_role(
            name="Muted",
            permissions=discord.Permissions(send_messages=False, speak=False),
            reason="Creation du role Muted pour mute des gens.")
        for channel in message.guild.channels:
            await channel.set_permissions(mutedRole, send_messages=False, speak=False)
        return mutedRole

    async def getMutedRole(message):
        roles = message.guild.roles
        for role in roles:
            if role.name == "Muted":
                return role
        return await createMutedRole(message)

    # Start the bot
    client.run(settings.BOT_TOKEN)


###############################################################################

if __name__ == "__main__":
    main()
