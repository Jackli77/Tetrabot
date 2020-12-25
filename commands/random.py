from discord import Client
from numpy.random import randint

from commands.base_command import BaseCommand


class Random(BaseCommand):

    def __init__(self):
        description = "Donne un nombre aléatoire entre 1 et 100, les bornes peuvent etre spécifiées en argument"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        lower = 1
        upper = 100
        if len(params) > 1:
            try:
                lower = int(params[0])
                upper = int(params[1])
            except ValueError:
                await message.channel.send("Ecris un nombre")
                return
        elif len(params) > 0:
            try:
                upper = int(params[0])
            except ValueError:
                await message.channel.send("Ecris des nombres")
                return
        if lower > upper:
            await message.channel.send(
                "{0}, The lower bound can't be higher than the upper bound!".format(message.author.mention))
            return
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        rolled = randint(lower, upper + 1)
        msg = "<:game_die:791035424507691013> **{0}**. La roulette va de **{1}** à **{2}** <:game_die:791035424507691013>".format(
            aut_usr.display_name, lower, upper) + "\n" \
              + "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! **{1}**<:game_die:791035424507691013>".format(
            rolled, aut_usr.display_name)
        await message.channel.send(msg)
