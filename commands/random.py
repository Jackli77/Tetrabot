from discord import Client

from commands.base_command import BaseCommand
from numpy.random import randint


# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase
# So, a command class named Random will generate a 'random' command
class Random(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Donne un nombre aléatoire entre 1 et 100, les bornes peuvent etre spécifiées en argument"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params' 
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = []
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
        rolled = randint(lower, upper+1)
        msg = "<:game_die:791035424507691013> **{0}**. La roulette va de **{1}** à **{2}** <:game_die:791035424507691013>".format(aut_usr.display_name, lower, upper) + "\n" \
              + "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! **{1}**<:game_die:791035424507691013>".format(rolled,aut_usr.display_name)
        await message.channel.send(msg)
