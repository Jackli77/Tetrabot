from asyncio import sleep
from commands.base_command import BaseCommand

class Clean(BaseCommand):

    def __init__(self):
        description = "Supprime un nombre donné de messages"
        params = ["nombre"]
        aliases = ["c"]
        super().__init__(description, params, aliases=aliases)

    async def handle(self, params: int, message,client):
        max = int(params[0])
        messages = [m async for m in message.channel.history(limit=max + 1)]
        c = 0
        cleaning_msg = await message.channel.send("Cleaning...")
        for message in messages:
            c += 1
            await message.delete()
            await sleep(0.5)
        await cleaning_msg.delete()
