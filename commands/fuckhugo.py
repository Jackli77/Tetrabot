from commands.base_command  import BaseCommand
from utils                  import get_emoji


# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase

# So, a command class named Random will generate a 'random' command
class fu(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Insulte Hugo"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        await message.channel.send("Fuck Hugo" + get_emoji(":Vibrator:"))
