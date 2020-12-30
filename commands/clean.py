from asyncio import sleep
from commands.base_command import BaseCommand

class c(BaseCommand):

    def __init__(self):
        description = "Supprime @param message"
        params = ["nombre"]
        super().__init__(description, params)

    async def handle(self, params: int, message,client):
        max = int(params[0])
        messages = await message.channel.history(limit=max + 1).flatten()
        c = 0
        cleaning_msg = await message.channel.send("Cleaning...")
        for message in messages:
            c += 1
            await message.delete()
            await sleep(0.5)
        await cleaning_msg.delete()
