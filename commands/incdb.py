from discord import Client
from commands.base_command import BaseCommand
from database_init import users


def winrate(win, loss):
    if win == 0:
        return 0
    return 100 * win // (win + loss)


async def incdb(aut_id, gain):
    """Upsert a user record and increment stats. Returns the updated document."""
    # Ensure the user document exists
    await users.update_one(
        {"_id": aut_id},
        {"$setOnInsert": {"val": 0, "equity": 0, "win": 0, "loss": 0}},
        upsert=True
    )

    # Build the increment payload
    inc_fields = {"val": 1, "equity": gain}
    if gain < 0:
        inc_fields["loss"] = 1
    elif gain > 0:
        inc_fields["win"] = 1

    doc = await users.find_one_and_update(
        {"_id": aut_id},
        {"$inc": inc_fields},
        return_document=True  # return the document AFTER the update
    )
    # Return as a tuple matching the old psycopg2 shape: (val, equity, win, loss)
    return [(doc["val"], doc["equity"], doc["win"], doc["loss"])]


class inc(BaseCommand):

    def __init__(self):
        description = "Increments the counter of the MongoDB database"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        aut_id = int(''.join(filter(str.isdigit, message.author.mention)))
        aut_usr = await client.fetch_user(aut_id)
        records = await incdb(aut_id, 0)
        wr = winrate(records[0][2], records[0][3])
        await message.channel.send(
            f"**{aut_usr.display_name}** score:**{records[0][0]}** "
            f"équité:**{records[0][1]}** WR:**{records[0][2]}/{records[0][3]} {wr}%**"
        )