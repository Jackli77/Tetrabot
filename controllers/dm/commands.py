import settings
from dms.base_dm import BaseDm


# This is a convenient command that automatically generates a helpful
# message showing all available commands.  It reuses the exact same embed
# renderer as /commands and !commands so the formats can never drift.
class Commands(BaseDm):

    def __init__(self):
        description = "Affiche la liste de toutes les commandes disponibles"
        params = None
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Imported lazily: message_handler imports the commands package, whose
        # help command imports dms_handler (no import cycle at load time).
        from message_handler import COMMAND_HANDLERS
        from dms_handler import DMS_HANDLERS
        from views.formatting import render_help

        embed = render_help(settings.COMMAND_PREFIX, COMMAND_HANDLERS, DMS_HANDLERS)
        await message.author.send(embed=embed)
