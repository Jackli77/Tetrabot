from datetime import *

from cronevents.base_cronevent import BaseCronEvent
from utils import get_channel


class Waifu_time(BaseCronEvent):

    def __init__(self):
        super().__init__(minute=28, second=1)

    async def run(self, client):
        now = datetime.now()
        msg = f"<@&582978303086952452> Il est maintenant **{now.hour}:{now.minute}**, autrement dit l'heure des waifus"
        channel = get_channel(client, "waifu")
        await channel.send(msg)
