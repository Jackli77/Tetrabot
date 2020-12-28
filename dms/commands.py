from dms.base_dm import BaseDm


# This is a convenient command that automatically generates a helpful
# message showing all available commands
class Commands(BaseDm):

    def __init__(self):
        description = "Affiche ce message d'aide"
        params = None
        super().__init__(description, params)

    async def handle(self, params, message, client):
        from dms_handler import DMS_HANDLERS
        msg = message.author.mention + "\n"

        # Displays all descriptions, sorted alphabetically by command name
        for cmd in sorted(DMS_HANDLERS.items()):
            msg += "\n" + cmd[1].description

        await message.author.send(msg)
