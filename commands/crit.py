import asyncio
from discord import Client
from commands.base_command import BaseCommand
from asyncio import sleep
from numpy.random import randint

from commands.incdb import incdb


class crit(BaseCommand):

    def __init__(self):
        description = "Lance un crit avec la première personne qui react"
        params = ["somme"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        channel = message.channel
        manche = 0
        crit1 = 0
        crit2 = 0
        odds = 15
        slep = 1
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        if len(params) > 1:
            try:
                argent = int(params[0])
                odds = int(params[1])
            except ValueError:
                await channel.send("Précise la somme mise en jeu")
                return
            if argent < 0 or 10 > odds or odds > 90:
                await channel.send(
                    "{}, Value error: pas de nombres négatfis, odds compris entre 10 et 90".format(aut_usr.mention))
                return
        elif len(params) > 0:
            try:
                argent = int(params[0])
            except ValueError:
                await channel.send("Précise la somme mise en jeu")
                return
            if argent < 0:
                await channel.send(
                    "{0}, Value error: pas de nombres négatfis,".format(aut_usr.mention))
                return
        else:
            return
        msg0 = "**{}** mise **{}** dans un duel de chafer crit **{}%**".format(aut_usr.mention, argent, odds)
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
        else:
            await channel.send(f'**{adv_usr.mention}** a accepté le challenge de {aut_usr.mention}')
        msg1 = "**{} Coup critique!**<:bangbang:791122260046905355>".format(aut_usr.display_name)
        msg2 = "**{} Coup critique!**<:bangbang:791122260046905355>".format(adv_usr.display_name)
        msg3 = "Pas de chance, **{}** <:8219_cheems:720974989490389043>".format(aut_usr.display_name)
        msg4 = "Pas de chance, **{}** <:8219_cheems:720974989490389043>".format(adv_usr.display_name)
        while crit1 == crit2:
            await sleep(slep)
            manche += 1
            await channel.send("__**Manche {}**__".format(manche))

            await sleep(slep)
            crited1 = randint(0, 100) < odds
            if crited1:
                crit1 += 1
                await channel.send(msg1)
            else:
                await channel.send(msg3)

            await sleep(slep)
            crited2 = randint(0, 100) < odds
            if crited2:
                crit2 += 1
                await channel.send(msg2)
                if crited1:
                    argent *= 2
                    await channel.send(
                        "La somme en jeu passe à **{}** <:money_with_wings:791121758774231050>".format(argent))
            else:
                await channel.send(msg4)

        await sleep(slep)
        msg5 = "Le duel s'est terminé après **{}** manches et **{}** égalités".format(manche, min(crit1, crit2))
        msg6 = "Le gagnant est **{0}**, **{1}** doit donner **{2}** à **{0}** <:money_with_wings:791121758774231050>".format(
            aut_usr.display_name, adv_usr.display_name, argent)
        msg7 = "Le gagnant est **{0}**, **{1}** doit donner **{2}** à **{0}** <:money_with_wings:791121758774231050>".format(
            adv_usr.display_name, aut_usr.display_name, argent)
        if crit1 > crit2:
            await channel.send(msg5 + "\n" + msg6)
            rec1 = incdb(aut_id, argent)
            rec2 = incdb(adv_usr.id, -argent)
            await message.channel.send(
                f"**{aut_usr.display_name}** a un score de **{rec1[0][0]}** et une équité de **{rec1[0][1]}**")
            await message.channel.send(
                f"**{adv_usr.display_name}** a un score de **{rec2[0][0]}** et une équité de **{rec2[0][1]}**")
        else:
            await channel.send(msg5 + "\n" + msg7)
            rec1 = incdb(aut_id, -argent)
            rec2 = incdb(adv_usr.id, argent)
            await message.channel.send(
                f"**{aut_usr.display_name}** a un score de **{rec1[0][0]}** et une équité de **{rec1[0][1]}**")
            await message.channel.send(
                f"**{adv_usr.display_name}** a un score de **{rec2[0][0]}** et une équité de **{rec2[0][1]}**")