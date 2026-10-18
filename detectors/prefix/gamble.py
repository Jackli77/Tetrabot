import asyncio

from detectors.prefix.base_command import BaseCommand


# The !gamble command: challenges another user to a dice-roll duel.
# Only the prefix-specific parts live here (argument parsing + the ✅ reaction
# challenge); the shared duel logic lives in controllers.commands.cmd_gamble.
# Command name: !gamble
class gamble(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Challenge @user à un gamble"
        # The command expects one parameter: the maximum roll (limite).
        params = ["limite"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        from controllers import LOGIC

        channel = message.channel

        # Parse the upper bound from the first argument.
        try:
            upper = int(params[0])
        except ValueError:
            await channel.send("Ecris la somme maximale séparée d'un espace")
            return

        if upper < 1:
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
        except asyncio.TimeoutError:
            await channel.send('Timeout')
            return

        # Hand over to the shared duel logic against the acceptor.
        ctx = self.build_context(params, message, client)
        await LOGIC["cmd_gamble"](ctx, user, upper)
