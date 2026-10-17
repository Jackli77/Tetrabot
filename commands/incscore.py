import asyncio

import discord
from commands.base_command import BaseCommand
from database_init import users
from commands.incdb import winrate


# The !incscore command: shows a paginated leaderboard of all players sorted by equity.
# Aliases: !leaderboard, !lb, !classement
# Command name: !incscore
class incscore(BaseCommand):

    def __init__(self):
        description = "Affiche le classement (leaderboard) des joueurs par équité"
        params = []
        aliases = ["leaderboard", "lb", "classement"]
        super().__init__(description, params, aliases=aliases)

    async def handle(self, params, message, client):
        channel = message.channel

        # Fetch all users from MongoDB, sorted by equity descending (richest first).
        records = await users.find().sort("equity", -1).to_list(length=None)

        if not records:
            await channel.send("Aucun joueur enregistré.")
            return

        # --- Page 1: Full leaderboard ---------------------------------------
        page1 = discord.Embed(title="Classement d'equité", colour=discord.Colour.lighter_grey())
        top_usr = await client.fetch_user(records[0]["_id"])
        page1.set_thumbnail(url=top_usr.display_avatar.url)
        page1.add_field(
            name="Membres",
            value="\n ".join(
                f"**{r.get('username', str(r['_id']))}** - "
                f"**WR:**{r['win']}/{r['loss']} {winrate(r['win'], r['loss'])}% - "
                f"**Equité:**{r['equity']}"
                for r in records
            ),
            inline=False
        )

        # --- Page 2: Top player ---------------------------------------------
        page2 = discord.Embed(
            title='Grand gagnant',
            description=(
                f"**{records[0].get('username', str(records[0]['_id']))}** avec une équité de "
                f"**{records[0]['equity']}** et un winrate de "
                f"**{records[0]['win']}/{records[0]['loss']} "
                f"{winrate(records[0]['win'], records[0]['loss'])}%**"
            ),
            colour=discord.Colour.green()
        )
        page2.set_thumbnail(url=top_usr.display_avatar.url)

        # --- Page 3: Bottom player ------------------------------------------
        bot_usr = await client.fetch_user(records[-1]["_id"])
        page3 = discord.Embed(
            title='Grand perdant',
            description=(
                f"**{records[-1].get('username', str(records[-1]['_id']))}** avec une équité de "
                f"**{records[-1]['equity']}** et un winrate de "
                f"**{records[-1]['win']}/{records[-1]['loss']} "
                f"{winrate(records[-1]['win'], records[-1]['loss'])}%**"
            ),
            colour=discord.Colour.red()
        )
        page3.set_thumbnail(url=bot_usr.display_avatar.url)

        pages = [page1, page2, page3]
        msg_pg1 = await channel.send(embed=page1)

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
            if emoji == '▶' and i < 2:
                i += 1
                await msg_pg1.edit(embed=pages[i])
            if emoji == '⏭':
                i = 2
                await msg_pg1.edit(embed=pages[i])
