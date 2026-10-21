"""COMMAND handlers: the shared behaviour behind every command.

Each handler follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Two controllers feed this shared behaviour — :mod:`tetrabot.controllers.prefix`
(``!``) and :mod:`tetrabot.controllers.slash` (``/``) — so one implementation
serves both.  This package stays controller-free: it only exposes the
context, the ``cmd_*`` implementations, and the ``HANDLERS`` registry.

To add a new command:
    1. Write ``async def cmd_foo(ctx)`` in :mod:`tetrabot.controllers.commands.logic`
       (or :mod:`tetrabot.controllers.commands.duels`).
    2. Add a :class:`tetrabot.catalog.CommandSpec` describing it.
    3. Done — both transports pick it up automatically.
"""
from tetrabot.controllers.commands import chat, duels, logic
from tetrabot.controllers.commands.chat import cmd_forget, cmd_listen
from tetrabot.controllers.commands.duels import cmd_crit, cmd_gamble
from tetrabot.controllers.commands.logic import (
    cmd_aup,
    cmd_clean,
    cmd_help,
    cmd_inc,
    cmd_incscore,
    cmd_random,
)

#: Every shared command implementation, keyed by name.  The controllers look
#: their commands up here, so the catalog never has to know about functions.
HANDLERS = {
    "cmd_aup": cmd_aup,
    "cmd_clean": cmd_clean,
    "cmd_crit": cmd_crit,
    "cmd_forget": cmd_forget,
    "cmd_gamble": cmd_gamble,
    "cmd_help": cmd_help,
    "cmd_inc": cmd_inc,
    "cmd_incscore": cmd_incscore,
    "cmd_listen": cmd_listen,
    "cmd_random": cmd_random,
}

__all__ = [
    "HANDLERS",
    "chat",
    "cmd_aup",
    "cmd_clean",
    "cmd_crit",
    "cmd_forget",
    "cmd_gamble",
    "cmd_help",
    "cmd_inc",
    "cmd_incscore",
    "cmd_listen",
    "cmd_random",
    "duels",
    "logic",
]
