import random
from asyncio import sleep

from commands.base_command import BaseCommand


# Your friendly example event
# Keep in0 mind that the command name will be derived from the class name
# but in lowercase

# So, a command class named Random will generate a 'random' command
class c(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Supprime @param message"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["nombre"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params: int, message,client):
        max = int(params[0])
        print(max)
        messages = await message.channel.history(limit=max + 1).flatten()
        cpt = max + 1
        c = 0
        cleaning_msg = await message.channel.send("Cleaning...")
        for message in messages:
            c += 1
            await message.delete()
            await sleep(0.5)
        await cleaning_msg.delete()
