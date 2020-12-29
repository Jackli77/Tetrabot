from discord import Client
from commands.base_command import BaseCommand

class rig(BaseCommand):

    def __init__(self):
        description = "Rigs the money games"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        channel = message.channel
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        msg0 = "**{}** the games have been successfully rigged".format(aut_usr.display_name)
        bet_msg = await channel.send(msg0)
        await bet_msg.add_reaction('✅')
