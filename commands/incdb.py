from discord import Client
from commands.base_command import BaseCommand
from database_init import conn

class inc(BaseCommand):

    def __init__(self):
        description = "Increments the counter of a SQL database"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users
                (userid, val)
            SELECT %(id)s, 0
            WHERE
                NOT EXISTS (
                    SELECT userid FROM users WHERE userid = %(id)s
                );
            """,
            {'id' : aut_id})
        # Execute a query
        cur.execute("""
            UPDATE users 
            SET val = val + 1 
            WHERE userid = %(id)s
            """,
            {'id' : aut_id})
        # Retrieve query results
        cur.execute("""
                    SELECT val FROM users WHERE userid = %(id)s
                    """,
                    {'id': aut_id})
        records = cur.fetchall()
        conn.commit()
        cur.close()
        await message.channel.send(f"**{aut_usr.display_name}** a un score de {records[0][0]}")
