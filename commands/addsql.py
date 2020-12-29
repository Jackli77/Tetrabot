from discord import Client
from commands.base_command import BaseCommand
import os
import psycopg2

#Connect to DB
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
# Open a cursor to perform database operations
cur = conn.cursor()

# Execute a query
cur.execute("SELECT * FROM my_data")

# Retrieve query results
records = cur.fetchall()

class addsql(BaseCommand):

    def __init__(self):
        description = "Increments the counter of a SQL database"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        await message.channel.send(records)
