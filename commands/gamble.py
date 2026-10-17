import asyncio

from discord import Client

from commands.base_command import BaseCommand
from asyncio import sleep
from numpy.random import randint


# The !gamble command: challenges another user to a dice-roll duel.
# Both players roll a random number in [1, limite]; the higher roll wins the difference.
# The loser pays the winner the difference in "kakeras".
# Command name: !gamble
from commands.incdb import incdb


class gamble(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Challenge @user à un gamble"
        # The command expects one parameter: the maximum roll (limite).
        params = ["limite"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        channel = message.channel
        lower = 1

        # Parse the upper bound from the first argument.
        try:
            upper = int(params[0])
        except ValueError:
            await channel.send("Ecris la somme maximale séparée d'un espace")
            return

        if lower > upper:
            await channel.send(
                "{0}, rentre un nombre strictement positif".format(message.author.mention))
            return

        # Resolve the author's Discord user ID from their mention string.
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await client.fetch_user(aut_id)

        # Announce the gamble and add a ✅ reaction for opponents to accept.
        msg0 = "**{}** lance un gamble cappé à **{}**".format(aut_usr.mention, upper)
        bet_msg = await channel.send(msg0)
        await bet_msg.add_reaction('✅')

        # Only accept a ✅ on the bet message from a non-bot user.
        def check(reaction, user):
            return str(reaction.emoji) == '✅' and reaction.message == bet_msg and not user.bot

        # Wait up to 45 seconds for someone to accept the challenge.
        try:
            reaction, user = await client.wait_for('reaction_add', timeout=45.0, check=check)
            adv_usr = user
        except asyncio.TimeoutError:
            await channel.send('Timeout')
            return

        # Both players roll a random number in [lower, upper].
        rolled1 = randint(lower, upper + 1)
        rolled2 = randint(lower, upper + 1)

        msg1 = "<:game_die:791035424507691013> {0} vs {1}. La roulette va de **{2}** à **{3}** <:game_die:791035424507691013>".format(
            message.author.mention, adv_usr.mention, lower, upper)
        msg2 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(
            rolled1, aut_usr.display_name)
        msg3 = "<:game_die:791035424507691013> La mère d'Hugo vient de tirer un **{0}**! pour **{1}** <:game_die:791035424507691013>".format(
            rolled2, adv_usr.display_name)

        # Determine the winner and the payout difference.
        if rolled1 < rolled2:
            if rolled2 - rolled1 >= upper / 2:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name, adv_usr.display_name, rolled2 - rolled1)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    aut_usr.display_name, adv_usr.display_name, rolled2 - rolled1)
        elif rolled2 < rolled1:
            if rolled1 - rolled2 > upper / 2:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** s'est bien fait baiser et doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name, aut_usr.display_name, rolled1 - rolled2)
            else:
                msg4 = "<:game_die:791035424507691013> Le gagnant est **{0}**! **{1}** doit **{2}** kakeras à **{0}** <:game_die:791035424507691013>".format(
                    adv_usr.display_name, aut_usr.display_name, rolled1 - rolled2)
        else:
            msg4 = "<:8219_cheems:720974989490389043> égalité pas de gagnant <:8219_cheems:720974989490389043>"

        # Send the results with dramatic pauses between rolls.
        await message.channel.send(msg1)
        await sleep(2)
        await message.channel.send(msg2)
        await sleep(2)
        await message.channel.send(msg3)
        await sleep(2)
        await message.channel.send(msg4)

        # Update the database: winner gains the difference, loser loses it.
        rec1 = await incdb(aut_id, rolled2 - rolled1)
        rec2 = await incdb(adv_usr.id, rolled1 - rolled2)
        await message.channel.send(
            f"**{aut_usr.display_name}** a un score de **{rec1[0][0]}** et une équité de **{rec1[0][1]}**")
        await message.channel.send(
            f"**{adv_usr.display_name}** a un score de **{rec2[0][0]}** et une équité de **{rec2[0][1]}**")
