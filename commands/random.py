from discord import Client

from commands.base_command import BaseCommand
from numpy.random import randint


# The !random command: rolls a random number between 1 and 100 (or custom bounds if given).
# Usage: !random [lower] [upper]
# Command name: !random
class Random(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Donne un nombre aléatoire entre 1 et 100, les bornes peuvent etre spécifiées en argument"
        # This command takes zero to two optional parameters.
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Default bounds.
        lower = 1
        upper = 100
        # Parse optional arguments: !random [lower] [upper]
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
        # Validate that lower is not greater than upper.
        if lower > upper:
            await message.channel.send(
                "{0}, The lower bound can't be higher than the upper bound!".format(message.author.mention))
            return
        # Resolve the author's Discord user ID from their mention string.
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await client.fetch_user(aut_id)
        # Roll a random integer in [lower, upper] inclusive.
        rolled = randint(lower, upper + 1)
        # Compose the result message with dice emojis.
        msg = "<:game_die:791035424507691013> **{0}**. La roulette va de **{1}** à **{2}** <:game_die:791035424507691013>".format(aut_usr.display_name, lower, upper) + "\n" \
              + "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! **{1}**<:game_die:791035424507691013>".format(rolled,aut_usr.display_name)
        await message.channel.send(msg)
