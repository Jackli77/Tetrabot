import asyncio
import random
from commands.base_command import BaseCommand

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase

# So, a command class named Random will generate a 'random' command
class top(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Calcule ton bénéf sur un exo"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
            channel = message.channel
            await channel.send('Send me that 👍 reaction, mate')
            def check(reaction, user):
                return str(reaction.emoji) == '👍'
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await channel.send('👎')
            else:
                await channel.send('👍')
