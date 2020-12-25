from discord import Client

from commands.base_command import BaseCommand
from asyncio import sleep
from numpy.random import randint

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase
# So, a command class named Random will generate a 'random' command
class crit(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Challenge @user à un chafer crit"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["adversaire","somme"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        # 'params' is a list that contains the parameters that the command
        # expects to receive, t is guaranteed to have AT LEAST as many
        # parameters as specified in __init__
        # 'message' is the discord.py Message object for the command to handle
        # 'client' is the bot Client object
        manche = 0
        crit1 = 0
        crit2 = 0
        try:
            adversaire = params[0]
            argent = int(params[1])
        except ValueError:
            await message.channel.send("Mentionne qqun puis écris la somme misée séparée d'un espace")
            return
        if argent < 0:
            await message.channel.send(
                "{0}, Rentre un nombre positif?".format(message.author.mention))
            return
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        ad_id = int(''.join(filter(str.isdigit, adversaire)))
        adv_usr = await Client.fetch_user(client, ad_id)
        aut_usr = await Client.fetch_user(client, aut_id)
        msg0 = "**{}** challenge **{}** à un duel de chafer crit!".format(aut_usr.mention,adv_usr.mention)
        msg1 = "**{} Coup critique!**<:bangbang:791122260046905355>".format(aut_usr.display_name)
        msg2 = "**{} Coup critique!**<:bangbang:791122260046905355>".format(adv_usr.display_name)
        msg3 = "Pas de chance, **{}** <:8219_cheems:720974989490389043>".format(aut_usr.display_name)
        msg4 = "Pas de chance, **{}** <:8219_cheems:720974989490389043>".format(adv_usr.display_name)
        await message.channel.send(msg0)
        while crit1 == crit2:
            await sleep(2)
            manche += 1
            await message.channel.send("__**Manche {}**__".format(manche))

            await sleep(2)
            crited1 = randint(0, 100) < 15
            if crited1:
                crit1 += 1
                await message.channel.send(msg1)
            else:
                await message.channel.send(msg3)

            await sleep(2)
            crited2 = randint(0, 100) < 15
            if crited2:
                crit2 += 1
                await message.channel.send(msg2)
                if crited1:
                    argent *= 2
                    await message.channel.send("La somme en jeu passe à **{}** <:money_with_wings:791121758774231050>".format(argent))
            else:
                await message.channel.send(msg4)

        await sleep(2)
        msg5 = "Le duel s'est terminée après **{}** manches et **{}** égalités".format(manche, min(crit1, crit2))
        msg6 = "Le gagnant est **{0}**, **{1}** doit donner **{2}** à **{0}** <:money_with_wings:791121758774231050>".format(aut_usr.display_name, adv_usr.display_name, argent)
        msg7 = "Le gagnant est **{0}**, **{1}** doit donner **{2}** à **{0}** <:money_with_wings:791121758774231050>".format(adv_usr.display_name, aut_usr.display_name, argent)
        if crit1 > crit2:
            await message.channel.send(msg5 + "\n" + msg6)
        else:
            await message.channel.send(msg5 + "\n" + msg7)
