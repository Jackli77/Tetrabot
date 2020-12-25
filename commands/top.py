import asyncio

from commands.base_command import BaseCommand


class top(BaseCommand):

    def __init__(self):
        description = "Top la"
        params = []
        super().__init__(description, params)

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
