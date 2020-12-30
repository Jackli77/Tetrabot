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
        cur.execute("SELECT userid,val,equity FROM users")
        records = cur.fetchall()
        def order(e):
            return e[1]
        records.sort(reverse=True,key=order)
        for row in records:
            usr = await Client.fetch_user(client, row[0])
            await message.channel.send(f"**<{usr.display_name}>** -- **{row[1]}** -- Equité:**{row[2]}**")
        cur.close()