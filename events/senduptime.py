from datetime import *

from events.base_event import BaseEvent
from utils import get_channel


class senduptime(BaseEvent):

    def __init__(self):
        interval_minutes = 60
        self.startime = datetime.now()
        super().__init__(interval_minutes)

    async def run(self, client):
        now = datetime.now()
        uptime = now - self.startime
        msg = f"J'ai été démarré il y a **{str(uptime).split('.', 2)[0]}**"
        channel = get_channel(client, "botactivity")
        await channel.send(msg)
