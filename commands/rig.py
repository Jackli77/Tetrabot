from discord import Client
from commands.base_command import BaseCommand


# The !rig command: a joke command that claims to "rig" the money games.
# Sends a message and adds a ✅ reaction to it.
# Command name: !rig
class rig(BaseCommand):

    def __init__(self):
        description = "Rigs the money games"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        channel = message.channel
        # Resolve the author's Discord user ID from their mention string.
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await client.fetch_user(aut_id)
        # Announce that the games have been rigged.
        msg0 = "**{}** the games have been successfully rigged".format(aut_usr.display_name)
        bet_msg = await channel.send(msg0)
        await bet_msg.add_reaction('✅')
