from discord import Client
from commands.base_command import BaseCommand
from database_init import conn

def winrate(win,loss):
    if win == 0:
        return 0
    else:
        return 100 * win // (win + loss)

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
                WHERE userid = %(id)s;
                UPDATE users
                SET equity = equity + %(gain)s
                WHERE userid = %(id)s;
                """,
                {'id': aut_id, 'gain': gain})
    if gain < 0:
        cur.execute("""
                UPDATE users 
                SET loss = loss + 1 
                WHERE userid = %(id)s;
                """)
    elif gain > 0:
        cur.execute("""
                    UPDATE users                         
                    SET win = win + 1 
                    WHERE userid = %(id)s;
                    """)
    # Retrieve query results
    cur.execute("""
                        SELECT val,equity,win,loss FROM users WHERE userid = %(id)s
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
        wr = winrate(records[0][2],records[0][3])
        await message.channel.send(f"**{aut_usr.display_name}** score:**{records[0][0]}** équité:**{records[0][1]}** WR:**{records[0][2]}/{records[0][3]} {wr}%**")