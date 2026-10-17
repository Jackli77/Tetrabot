from commands.base_command import BaseCommand


# The !random command: rolls a random number between 1 and 100 (or custom bounds if given).
# The shared logic lives in controllers.commands.cmd_random (it also serves /random).
# Usage: !random [lower] [upper]
# Command name: !random
class Random(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Donne un nombre aléatoire entre 1 et 100, les bornes peuvent etre spécifiées en argument"
        # This command takes zero to two optional parameters.
        params = []
        super().__init__(description, params)
