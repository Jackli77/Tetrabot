from commands.base_command import BaseCommand
from asyncio import sleep

# The !aup command: pings a target and repeatedly asks them to come ("au pied").
# Command name: !aup
class aup(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Fais venir @toutou au pièd"
        # The command expects one parameter: the target to ping.
        params = ["@toutou"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # params[0] is the mention or name of the person to call.
        toutou = params[0]
        # Initial ping.
        await message.channel.send("Au pièd,{} <:bontoutou:790992228301668352>".format(toutou))
        # Wait a few seconds before spamming follow-ups.
        await sleep(3)
        # Send 5 repetitive messages urging the target to come.
        for i in range(5):
            await message.channel.send('Viens ici %s et fais waf %s ' % (toutou,
                                                                     "<:bontoutou:790992228301668352>"))
