import asyncio
from discord import Client
from dms.base_dm import BaseDm

from utils import get_channel


class hot(BaseDm):

    def __init__(self):
        description = "Hot"
        params = ["max","nombre"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        channel = message.channel
        waifu = get_channel(client, "waifu")
        if len(params) > 2:
            try:
                max = int(params[0])
                nombre = int(params[1])
                raison = params[2]
            except ValueError:
                await channel.send("Max,nombre,raison")
                return
        else:
            try:
                max = int(params[0])
                nombre = int(params[1])
            except ValueError:
                await channel.send("Max,nombre")
                return
        if max < 0 or nombre < 0:
            await channel.send("{0}, Value error: pas de nombres négatfis,".format(aut_usr.mention))
            return
        await channel.send(f"{aut_id} a lancé un hot {max}, {raison}")

        def check(m, user):
            return m.content.isnumeric() and m.channel == waifu and not user.bot

        try:
            m, user = await client.wait_for('message', timeout=45.0, check=check)
            adv_usr = user
        except asyncio.TimeoutError:
            await channel.send('Timeout')
            return
        msg0 = "**{}** perdu, **{}** avait répondu **{}**".format(adv_usr.display_name)
        bet_msg = await waifu.send(msg0)
        await bet_msg.add_reaction('✅')
