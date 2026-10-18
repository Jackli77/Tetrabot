from commands.base_command import BaseCommand


# The !commands help command: lists every available server and DM command
# in a formatted Discord embed.  The shared logic lives in
# controllers.commands.cmd_help (it also serves /commands).
class Commands(BaseCommand):

    # The shared logic function for this command is named cmd_help.
    logic_key = "cmd_help"

    def __init__(self):
        description = "Affiche la liste de toutes les commandes disponibles"
        params = None
        super().__init__(description, params)
