import asyncio

from detectors.prefix.base_command import BaseCommand


# The !incscore command: shows a paginated leaderboard of all players sorted by equity.
# The embed pages are built by the shared controllers.commands.cmd_incscore; this
# class only keeps the prefix-specific reaction-based pagination UI.
# Aliases: !leaderboard, !lb, !classement
# Command name: !incscore
class incscore(BaseCommand):

    def __init__(self):
        description = "Affiche le classement (leaderboard) des joueurs par équité"
        params = []
        aliases = ["leaderboard", "lb", "classement"]
        super().__init__(description, params, aliases=aliases)

    async def handle(self, params, message, client):
        from controllers import LOGIC

        channel = message.channel
        ctx = self.build_context(params, message, client)
        pages = await LOGIC["cmd_incscore"](ctx)
        if not pages:
            await channel.send("Aucun joueur enregistré.")
            return

        msg_pg1 = await channel.send(embed=pages[0])

        # Add navigation reactions for pagination.
        await msg_pg1.add_reaction('⏮')  # First page
        await msg_pg1.add_reaction('◀')  # Previous page
        await msg_pg1.add_reaction('▶')  # Next page
        await msg_pg1.add_reaction('⏭')  # Last page

        i = 0  # Current page index

        # Only accept navigation reactions on this message from non-bot users.
        def check(reaction, user):
            return reaction.emoji in ('⏮', '◀', '▶', '⏭') and reaction.message == msg_pg1 and not user.bot

        # Wait for reactions to navigate pages; timeout after 45 seconds.
        while True:
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=45.0, check=check)
                emoji = str(reaction.emoji)
            except asyncio.TimeoutError:
                await msg_pg1.clear_reactions()
                return
            # Clean up the user's reaction after processing.
            if user != client.user:
                await msg_pg1.remove_reaction(reaction, user)
            if emoji == '⏮':
                i = 0
                await msg_pg1.edit(embed=pages[i])
            if emoji == '◀' and i > 0:
                i -= 1
                await msg_pg1.edit(embed=pages[i])
            if emoji == '▶' and i < len(pages) - 1:
                i += 1
                await msg_pg1.edit(embed=pages[i])
            if emoji == '⏭':
                i = len(pages) - 1
                await msg_pg1.edit(embed=pages[i])
