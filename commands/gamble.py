from asyncio import sleep

from discord import Client
from numpy.random import randint

from commands.base_command import BaseCommand


class gamble(BaseCommand):

    def __init__(self):
        description = "Challenge @user à un gamble"
        params = ["adversaire", "limite"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        lower = 1
        try:
            adversaire = params[0]
            upper = int(params[1])
        except ValueError:
            await message.channel.send("Mentionne qqun puis écris la somme maximale séparée d'un espace")
            return
        if lower > upper:
            await message.channel.send(
                "{0}, rentre un nombre strictement positif".format(message.author.mention))
            return
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        ad_id = int(''.join(filter(str.isdigit, adversaire)))
        adv_usr = await Client.fetch_user(client, ad_id)
        aut_usr = await Client.fetch_user(client, aut_id)
        rolled1 = randint(lower, upper + 1)
        rolled2 = randint(lower, upper + 1)
        msg1 = "<:game_die:791035424507691013> {0} vs {1}. La roulette va de **{2}** à **{3}** <:game_die:791035424507691013>".format(
            message.author.mention, adversaire, lower, upper)
        msg2 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(
            rolled1, aut_usr.display_name)
        msg3 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(
            rolled2, adv_usr.display_name)
        if rolled1 < rolled2:
            if (rolled2 - rolled1 >= upper / 2):
                "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name, adv_usr.display_name, rolled2 - rolled1)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name, adv_usr.display_name, rolled2 - rolled1)
        elif rolled2 < rolled1:
            if (rolled1 - rolled2 > upper / 2):
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name, aut_usr.display_name, rolled1 - rolled2)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name, aut_usr.display_name, rolled1 - rolled2)
        else:
            msg4 = "<:8219_cheems:720974989490389043> égalité pas de gagnant <:8219_cheems:720974989490389043>"
        await message.channel.send(msg1)
        await sleep(2)
        await message.channel.send(msg2)
        await sleep(2)
        await message.channel.send(msg3)
        await sleep(2)
        await message.channel.send(msg4)
