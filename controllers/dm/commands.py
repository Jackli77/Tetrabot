from config import settings
from controllers.dm.base_dm import BaseDm


# This is a convenient command that automatically generates a helpful
# message showing all available commands.  It reuses the exact same embed
# renderer as /commands and !commands so the formats can never drift.
class Commands(BaseDm):

    def __init__(self):
        description = "Affiche la liste de toutes les commandes disponibles"
        params = None
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Imported lazily: the prefix routers import command classes, whose
        # help command imports the dm router (no import cycle at load time).
        from controllers.dm.router import DMS_HANDLERS
        from controllers.prefix.router import COMMAND_HANDLERS
        from views.formatting import render_help

        embed = render_help(settings.COMMAND_PREFIX, COMMAND_HANDLERS, DMS_HANDLERS)
        await message.author.send(embed=embed)
