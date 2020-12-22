from events.base_event      import BaseEvent
from utils                  import get_channel
from datetime               import datetime


# Your friendly example event
# You can name this class as you like, but make sure to set BaseEvent
# as the parent class
class ExampleEvent(BaseEvent):

    def __init__(self):
        interval_minutes = 1 # Set the interval for this event
        super().__init__(interval_minutes)

    # Override the run() method
    # It will be called once every {interval_minutes} minutes
    async def run(self, client):
        now = datetime.now()
        if now.minute == 28:
            msg = f"Il est {now.hour}:{now.minute}, autrement dit l'heure des waifus"
            channel = get_channel(client, "waifu")
            await channel.send(msg)
