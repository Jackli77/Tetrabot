from commands.base_command import BaseCommand


# The !fh command: a simple joke command that replies "Fuck hugo!".
# Command name: !fh
class fh(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Fuck qui?"
        # This command takes no parameters.
        params = []
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Send the punchline.
        await message.channel.send("Fuck qui ?\nFuck hugo !")