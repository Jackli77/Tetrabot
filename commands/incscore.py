import asyncio

import discord
from commands.base_command import BaseCommand
from database_init import conn
from commands.incdb import winrate

class incscore(BaseCommand):

    def __init__(self):
        description = "Donne le tableau des inc scores"
        params = []
        super().__init__(description, params)


    async def handle(self, params, message, client):
        cur = conn.cursor()
        channel = message.channel
        cur.execute("SELECT username,equity,win,loss,userid FROM users")
        records = cur.fetchall()
        def order(e):
            return e[1]
        records.sort(reverse=True,key=order)
        cur.close()
        page1 = discord.Embed(title="Classement Tetrapodes", colour=discord.Colour.lighter_grey())
        usr = await discord.Client.fetch_user(client, records[0][4])
        page1.set_thumbnail(url=usr.avatar_url)
        page1.add_field(name="Membres", value="\n ".join(f"**{member[0]}** -- WR:**{winrate(member[2],member[3])}%** -- Equité:**{member[1]}**" for member in records), inline=False)
        page2 = discord.Embed(
            title='Grand gagnant',
            description=f'**{records[0][0]}** avec une équité de **{records[0][1]}** et un winrate de **{winrate(records[0][2],records[0][3])}%**',
            colour=discord.Colour.green()
        )
        page2.set_thumbnail(url=usr.avatar_url)
        page3 = discord.Embed(
            title='Grand perdant',
            description=f'**{records[-1][0]}** avec une équité de **{records[-1][1]}** et un winrate de **{winrate(records[-1][2],records[-1][3])}%**',
            colour=discord.Colour.red()
        )
        lsr = await discord.Client.fetch_user(client, records[-1][4])
        page3.set_thumbnail(url=lsr.avatar_url)

        pages = [page1, page2, page3]

        msg_pg1 = await channel.send(embed=page1)

        await msg_pg1.add_reaction('⏮')
        await msg_pg1.add_reaction('◀')
        await msg_pg1.add_reaction('▶')
        await msg_pg1.add_reaction('⏭')

        i = 0
        def check(reaction,user):
            return reaction.emoji in ('⏮','◀','▶','⏭') and reaction.message == msg_pg1 and not user.bot
        while True:
            try:
                reaction,user = await client.wait_for('reaction_add', timeout=45.0, check=check)
                emoji = str(reaction.emoji)
            except asyncio.TimeoutError:
                await msg_pg1.clear_reactions()
                return
            if str(user) != 'Tetrabot#2779':  # Example: 'MyBot#1111'
                await msg_pg1.remove_reaction(reaction, user)
            if emoji == '⏮':
                i = 0
                await msg_pg1.edit(embed=pages[i])
            if emoji == '◀':
                if i > 0:
                    i -= 1
                    await msg_pg1.edit(embed=pages[i])
            if emoji == '▶':
                if i < 2:
                    i += 1
                    await msg_pg1.edit(embed=pages[i])
            if emoji == '⏭':
                i = 2
                await msg_pg1.edit(embed=pages[i])
