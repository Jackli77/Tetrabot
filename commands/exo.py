import random
from commands.base_command import BaseCommand

# Your friendly example event
# Keep in mind that the command name will be derived from the class name
# but in lowercase

# So, a command class named Random will generate a 'random' command
class exo(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "Calcule ton bénéf sur un exo"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        prix = 30000
        if(len(params) > 0):
            prix = int(params[0])
        c = 1
        rep = random.randint(1, 100)
        r = random.randint(1, 100)
        while r != rep:
            c += 1
            r = random.randint(1, 100)

        if c == 1:
            await message.channel.send("%d tenta avant exo, %s" % (c, f"{prix * (100 - c):,}".replace(',', ' ')+ " kamas de benef"))
        elif c <= 100:
            await message.channel.send("%d tentas avant exo, %s" % (c, f"{prix * (100 - c):,}".replace(',', ' ')+ " kamas de benef"))
        else:
            await message.channel.send("%d tentas avant exo, %s" % (c, f"{prix * (c - 100):,}".replace(',', ' ')+ " kamas de perdu"))
