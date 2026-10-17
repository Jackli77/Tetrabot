from asyncio import sleep
from commands.base_command import BaseCommand


# The !clean command: deletes a given number of recent messages in the channel.
# Alias: !c
class Clean(BaseCommand):

    def __init__(self):
        description = "Supprime un nombre donné de messages"
        params = ["nombre"]
        aliases = ["c"]
        super().__init__(description, params, aliases=aliases)

    async def handle(self, params, message, client):
        # Number of messages to delete (from the first parameter).
        max = int(params[0])
        # Fetch `max + 1` recent messages (+1 to also remove the command message itself).
        messages = [m async for m in message.channel.history(limit=max + 1)]
        c = 0
        # Let the user know cleaning is in progress.
        cleaning_msg = await message.channel.send("Cleaning...")
        for message in messages:
            c += 1
            await message.delete()
            # Small delay to avoid hitting Discord rate limits.
            await sleep(0.5)
        # Remove the "Cleaning..." status message once done.
        await cleaning_msg.delete()
