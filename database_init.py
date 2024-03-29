import os
import psycopg2

# Connect to DB
from discord import Client

os.system("set DATABASE_URL=postgres://eccexmdcwmfbfs:ffc3c2b5fdee5036a8ccc050911f405773c568ec757870655c1142e9f3ace6c6"
          "@ec2-3-248-4-172.eu-west-1.compute.amazonaws.com:5432/d2tvutmq0s0kd0")

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')


async def initialize(client):
    # Open a cursor to perform database operations
    cur = conn.cursor()
    cur.execute("SELECT userid FROM users")
    records = cur.fetchall()
    cur.close()
    cur2 = conn.cursor()
    for id in records:

        name = await Client.fetch_user(client, id[0])
        cur2.execute("""
                    UPDATE users
                    SET username = %(name)s
                    WHERE userid = %(id)s;
                    """,
                    {'id': id, 'name': name.name})
    conn.commit()
    cur2.close()
