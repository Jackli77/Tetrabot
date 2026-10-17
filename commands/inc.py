from commands.base_command import BaseCommand


# The !inc command: displays the user's score, equity, and winrate.
# All behaviour lives in controllers.commands.cmd_inc — this class only
# provides the prefix-transport metadata (name, params, description).
# Command name: !inc
class inc(BaseCommand):

    def __init__(self):
        description = "Incrémente ton score"
        params = None
        super().__init__(description, params)
