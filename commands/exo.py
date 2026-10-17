import random
from commands.base_command import BaseCommand


# The !exo command: simulates an "exo" (exogem) attempt sequence in a Dofus-like game.
# Rolls until the target number is hit, then reports profit or loss based on attempts.
# Command name: !exo
class exo(BaseCommand):

    def __init__(self):
        description = "Calcule ton bénéf sur un exo"
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Cost per attempt in kamas (default 30000).
        prix = 30000
        if len(params) > 0:
            prix = int(params[0])

        c = 1                       # Attempt counter, starting at 1
        rep = random.randint(1, 100)  # Target roll needed to succeed
        r = random.randint(1, 100)    # Current roll

        # Keep rolling until we hit the target number.
        while r != rep:
            c += 1
            r = random.randint(1, 100)

        # If we succeed within 100 attempts, it's a profit; otherwise a loss.
        if c == 1:
            await message.channel.send("%d tenta avant exo, %s" % (c, f"{prix * (100 - c):,}".replace(',', ' ')+ " kamas de benef"))
        elif c <= 100:
            await message.channel.send("%d tentas avant exo, %s" % (c, f"{prix * (100 - c):,}".replace(',', ' ')+ " kamas de benef"))
        else:
            await message.channel.send("%d tentas avant exo, %s" % (c, f"{prix * (c - 100):,}".replace(',', ' ')+ " kamas de perdu"))
