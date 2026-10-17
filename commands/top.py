import asyncio
import random
from commands.base_command import BaseCommand


# The !top command: asks the channel for a 👍 reaction and responds accordingly.
# Command name: !top
class top(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Demande une réaction 👍 pour tester les réactions"
        # This command takes no parameters.
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        channel = message.channel
        await channel.send('Send me that 👍 reaction, mate')

        # Only accept a 👍 reaction.
        def check(reaction, user):
            return str(reaction.emoji) == '👍'

        try:
            reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await channel.send('👎')
        else:
            await channel.send('👍')
