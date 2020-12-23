from discord import Client

from commands.base_command import BaseCommand
from asyncio import sleep
from numpy.random import randint

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase
# So, a command class named Random will generate a 'random' command
class gamble(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Challenge @user à un gamble"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["adversaire","limite"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        # 'params' is a list that contains the parameters that the command
        # expects to receive, t is guaranteed to have AT LEAST as many
        # parameters as specified in __init__
        # 'message' is the discord.py Message object for the command to handle
        # 'client' is the bot Client object
        lower = 1
        try:
            adversaire = params[0]
            upper = int(params[1])
        except ValueError:
            await message.channel.send("Mentionne qqun puis écris la somme maximale séparée d'un espace")
            return
        if lower > upper:
            await message.channel.send(
                "{0}, rentre un nombre plus grand que 1".format(message.author.mention))
            return
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        ad_id = int(''.join(filter(str.isdigit,adversaire)))
        adv_usr = await Client.fetch_user(client,ad_id)
        aut_usr = await Client.fetch_user(client,aut_id)
        rolled1 = randint(lower, upper)
        rolled2 = randint(lower, upper)
        msg1 = "<:game_die:791035424507691013> {0} vs {1}. La roulette va de **{2}** à **{3}** <:game_die:791035424507691013>".format(message.author.mention, adversaire, lower, upper)
        msg2 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(rolled1,aut_usr.display_name)
        msg3 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(rolled2,adv_usr.display_name)
        if rolled1 < rolled2:
            msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                aut_usr.display_name,adv_usr.display_name, rolled2 - rolled1)
        else:
            msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                adv_usr.display_name,aut_usr.display_name, rolled1 - rolled2)
        await message.channel.send(msg1)
        await sleep(2)
        await message.channel.send(msg2)
        await sleep(2)
        await message.channel.send(msg3)
        await sleep(2)
        await message.channel.send(msg4)
