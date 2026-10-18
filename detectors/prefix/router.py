from detectors.prefix.base_command import BaseCommand

# This, in addition to the discovery below,
# imports all classes inside the detectors.prefix package.
from detectors.prefix import aup, clean, commands, crit, gamble, inc, incscore, random

from config import settings

# Register all available commands (including aliases)
COMMAND_HANDLERS = {}
for c in BaseCommand.__subclasses__():
    instance = c()
    COMMAND_HANDLERS[instance.name] = instance
    for alias in getattr(instance, "aliases", []):
        COMMAND_HANDLERS[alias.lower()] = instance

###############################################################################


async def handle_command(command, args, message, bot_client):
    # Check whether the command is supported, stop silently if it's not
    # (to prevent unnecessary spam if our bot shares the same command prefix
    # with some other bot)
    if command not in COMMAND_HANDLERS:
        return

    print(f"{message.author.name}: {settings.COMMAND_PREFIX}{command} " 
          + " ".join(args))

    # Retrieve the command
    cmd_obj = COMMAND_HANDLERS[command]
    if cmd_obj.params and len(args) < len(cmd_obj.params):
        await message.channel.send("{} Cette fonction à besoin de minimum {} arguments".format(message.author.mention, len(cmd_obj.params)))
    else:
        await cmd_obj.handle(args, message, bot_client)
