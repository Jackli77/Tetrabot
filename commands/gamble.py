import asyncio

from discord import Client

from commands.base_command import BaseCommand
from asyncio import sleep
from numpy.random import randint

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase
# So, a command class named Random will generate a 'random' command
from commands.incdb import incdb


class gamble(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Challenge @user à un gamble"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["limite"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        channel = message.channel
        lower = 1
        try:
            upper = int(params[0])
        except ValueError:
            await channel.send("Ecris la somme maximale séparée d'un espace")
            return
        if lower > upper:
            await channel.send(
                "{0}, rentre un nombre strictement positif".format(message.author.mention))
            return
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        msg0 = "**{}** lance un gamble cappé à **{}**".format(aut_usr.mention, upper)
        bet_msg = await channel.send(msg0)
        await bet_msg.add_reaction('✅')
        def check(reaction, user):
            return str(reaction.emoji) == '✅' and reaction.message == bet_msg and not user.bot

        try:
            reaction, user = await client.wait_for('reaction_add', timeout=45.0, check=check)
            adv_usr = user
        except asyncio.TimeoutError:
            await channel.send('Timeout')
            return
        rolled1 = randint(lower, upper+1)
        rolled2 = randint(lower, upper+1)
        msg1 = "<:game_die:791035424507691013> {0} vs {1}. La roulette va de **{2}** à **{3}** <:game_die:791035424507691013>".format(message.author.mention, adv_usr.mention, lower, upper)
        msg2 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(rolled1,aut_usr.display_name)
        msg3 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(rolled2,adv_usr.display_name)
        if rolled1 < rolled2:
            if(rolled2 - rolled1 >= upper/2):
                msg4 ="<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name, adv_usr.display_name, rolled2 - rolled1)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name,adv_usr.display_name, rolled2 - rolled1)
        elif rolled2 < rolled1:
            if(rolled1 - rolled2 > upper/2):
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name, aut_usr.display_name, rolled1 - rolled2)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name,aut_usr.display_name, rolled1 - rolled2)
        else:
            msg4 = "<:8219_cheems:720974989490389043> égalité pas de gagnant <:8219_cheems:720974989490389043>"
        await message.channel.send(msg1)
        await sleep(2)
        await message.channel.send(msg2)
        await sleep(2)
        await message.channel.send(msg3)
        await sleep(2)
        await message.channel.send(msg4)
        incdb(aut_id, rolled2 - rolled1)
        incdb(adv_usr.id, rolled1 - rolled2)
