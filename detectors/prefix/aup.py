from detectors.prefix.base_command import BaseCommand


# The !aup command: pings a target and repeatedly asks them to come ("au pied").
# The shared logic lives in controllers.commands.cmd_aup (it also serves /aup).
# Command name: !aup
class aup(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Fais venir @toutou au pièd"
        # The command expects one parameter: the target to ping.
        params = ["@toutou"]
        super().__init__(description, params)
