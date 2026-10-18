from controllers.prefix.base_command import BaseCommand


# The !clean command: deletes a given number of recent messages in the channel.
# The shared logic lives in controllers.commands.cmd_clean (it also serves /clean).
# Alias: !c
class Clean(BaseCommand):

    def __init__(self):
        description = "Supprime un nombre donné de messages"
        params = ["nombre"]
        aliases = ["c"]
        super().__init__(description, params, aliases=aliases)
