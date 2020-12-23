from events.base_event      import BaseEvent
from utils                  import get_channel
from datetime               import *


# Your friendly example event
# You can name this class as you like, but make sure to set BaseEvent
# as the parent class
class ExampleEvent(BaseEvent):

    def __init__(self):
        interval_minutes = 10  # Set the interval for this event
        self.startime = datetime.now()
        super().__init__(interval_minutes)

    # Override the run() method
    # It will be called once every {interval_minutes} minutes
    async def run(self, client):
        now = datetime.now()
        uptime = now - self.startime
        msg = f"Le serveur tourne depuis {str(uptime).split('.', 2)[0]}"
        channel = get_channel(client, "débug")
        await channel.send(msg)