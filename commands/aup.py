from asyncio import sleep

from commands.base_command import BaseCommand


class aup(BaseCommand):

    def __init__(self):
        description = "Fais venir @toutou au pièd"
        params = ["@toutou"]
        super().__init__(description, params)

    async def handle(self, params, message, client):
        toutou = params[0]
        await message.channel.send("Au pièd,{} <:bontoutou:790992228301668352>".format(toutou))
        await sleep(3)
        for i in range(5):
            await message.channel.send('Viens ici %s et fais waf %s ' % (toutou,
                                                                         "<:bontoutou:790992228301668352>"))
