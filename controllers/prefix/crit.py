import asyncio

from controllers.prefix.base_command import BaseCommand


# The !crit command: starts a "critical hit" duel between the author and the
# first user who reacts with ✅.
# Only the prefix-specific parts live here (argument parsing + the ✅ reaction
# challenge); the shared duel logic lives in controllers.commands.cmd_crit.
# Command name: !crit
class crit(BaseCommand):

    def __init__(self):
        description = "Lance un crit avec la première personne qui react"
        params = ["somme"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        from controllers import LOGIC

        channel = message.channel
        odds = 15           # Base crit chance percentage (10-90)

        # Resolve the author's Discord user ID from their mention string.
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await client.fetch_user(aut_id)
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

        # Announce the crit duel and add a ✅ reaction for opponents to accept.
        msg0 = "**{}** mise **{}** dans un duel de chafer crit **{}%**".format(aut_usr.mention, argent, odds)
        bet_msg = await channel.send(msg0)
        await bet_msg.add_reaction('✅')

        # Only accept a ✅ on the bet message from a non-bot user.
        def check(reaction, user):
            return str(reaction.emoji) == '✅' and reaction.message == bet_msg and not user.bot

        try:
            reaction, user = await client.wait_for('reaction_add', timeout=45.0, check=check)
        except asyncio.TimeoutError:
            await channel.send('Timeout')
            return
        else:
            await channel.send(f'**{user.mention}** a accepté le challenge de {aut_usr.mention}')

        # Hand over to the shared duel logic against the acceptor.
        ctx = self.build_context(params, message, client)
        await LOGIC["cmd_crit"](ctx, user, argent, odds)
