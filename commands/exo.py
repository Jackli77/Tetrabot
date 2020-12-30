import random
from commands.base_command import BaseCommand

class exo(BaseCommand):

    def __init__(self):
        description = "Calcule ton bénéf sur un exo"
        params = []
        super().__init__(description, params)

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
