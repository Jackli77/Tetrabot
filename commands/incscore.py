import asyncio

import discord
from discord import Client, Embed
from commands.base_command import BaseCommand
from database_init import conn

class incscore(BaseCommand):

    def __init__(self):
        description = "Donne le tableau des inc scores"
        params = []
        super().__init__(description, params)


    async def handle(self, params, message, client):
        cur = conn.cursor()
        channel = message.channel
        cur.execute("SELECT username,val,equity FROM users")
        records = cur.fetchall()
        def order(e):
            return e[1]
        records.sort(reverse=True,key=order)
        cur.close()
        page1 = discord.Embed(title="Server name", color=0x00ff00)
        page1.add_field(name="Member List:", value="\n ".join(f"**{member[0]}** -- **{member[1]}** -- Equité:**{member[2]}**" for member in records), inline=False)
        page2 = discord.Embed(
            title='Page 2/3',
            description='Description',
            colour=discord.Colour.orange()
        )
        page3 = discord.Embed(
            title='Page 3/3',
            description='Description',
            colour=discord.Colour.orange()
        )

        pages = [page1, page2, page3]

        msg_pg1 = await message.channel.send(embed=page1)

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
