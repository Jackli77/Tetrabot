from dms.base_dm import BaseDm

# This, in addition to tweaking __all__ on commands/__init__.py, 
# imports all classes inside the commands package.
from commands               import *

import settings

# Register all available commands
DMS_HANDLERS = {c.__name__.lower(): c()
                    for c in BaseDm.__subclasses__()}

###############################################################################


async def handle_command(command, args, message, bot_client):
    # Check whether the command is supported, stop silently if it's not
    # (to prevent unnecesary spam if our bot shares the same command prefix 
    # with some other bot)
    if command not in DMS_HANDLERS:
        return

    print(f"{message.author.name}: {settings.COMMAND_PREFIX}{command} " 
          + " ".join(args))

    # Retrieve the command
    cmd_obj = DMS_HANDLERS[command]
    if cmd_obj.params and len(args) < len(cmd_obj.params):
        await message.channel.send("{} Cette fonction à besoin de minimum {} arguments".format(message.author.mention, len(cmd_obj.params)))
    else:
        await cmd_obj.handle(args, message, bot_client)
