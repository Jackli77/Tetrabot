from cronevents.base_cronevent import BaseCronEvent
from utils                  import get_channel
from datetime               import *


# Your friendly example event
# You can name this class as you like, but make sure to set BaseEvent
# as the parent class
class Waifu_time(BaseCronEvent):

    def __init__(self):
        super().__init__(minute = 28,second = 1)

    # Override the run() method
    async def run(self, client):
        now = datetime.now()
        msg = f"<@&582978303086952452> Il est maintenant {now.hour}:{now.minute}, autrement dit l'heure des waifus"
        channel = get_channel(client, "waifu")
        await channel.send(msg)