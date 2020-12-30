from discord import Client
from commands.base_command import BaseCommand
from database_init import conn

def incdb(aut_id,gain):
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
        {'id': aut_id})
    # Execute a query
    cur.execute("""
                UPDATE users 
                SET val = val + 1 
                SET equity = equity + %(gain)s
                WHERE userid = %(id)s
                """,
                {'id': aut_id,'gain' : gain})
    # Retrieve query results
    cur.execute("""
                        SELECT val,equity FROM users WHERE userid = %(id)s
                        """,
                {'id': aut_id})
    records = cur.fetchall()
    conn.commit()
    cur.close()
    return records


class inc(BaseCommand):

    def __init__(self):
        description = "Increments the counter of the SQL database"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await Client.fetch_user(client, aut_id)
        records = incdb(aut_id,0)
        await message.channel.send(f"**{aut_usr.display_name}** a un score de {records[0][0]} et une équité de **{records[0][1]}**")