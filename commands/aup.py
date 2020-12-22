from commands.base_command import BaseCommand
from asyncio import sleep
from discord import User

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase

# So, a command class named Random will generate a 'random' command
class aup(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Fais venir @User au pièd"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["toutou"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        toutou = params[0]
        await message.channel.send("Au pièd <:bontoutou:790992228301668352>")
        await sleep(3)
        for i in range(5):
            await message.channel.send('Viens ici %s et fais waf %s ' % (toutou,
                                                                     "<:bontoutou:790992228301668352>"))
