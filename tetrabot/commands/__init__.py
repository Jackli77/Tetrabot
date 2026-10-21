"""COMMAND layer: transport-agnostic command implementations.

Each ``cmd_*`` function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Two detectors feed this shared logic — :mod:`tetrabot.detectors.prefix` (``!``)
and :mod:`tetrabot.detectors.slash` (``/``) — so one implementation serves
both.  This package stays detector-free: it only exposes the context, the
``cmd_*`` implementations, and the ``LOGIC`` registry.

To add a new command:
    1. Write ``async def cmd_foo(ctx)`` in :mod:`tetrabot.commands.logic`
       (or :mod:`tetrabot.commands.duels`).
    2. Add a :class:`tetrabot.catalog.CommandSpec` describing it.
    3. Done — both transports pick it up automatically.
"""
from tetrabot.commands import duels, logic
from tetrabot.commands.duels import cmd_crit, cmd_gamble
from tetrabot.commands.logic import (
    cmd_aup,
    cmd_chat,
    cmd_clean,
    cmd_help,
    cmd_inc,
    cmd_incscore,
    cmd_random,
)

#: Every shared command implementation, keyed by name.  The detectors look
#: their commands up here, so the catalog never has to know about functions.
LOGIC = {
    "cmd_aup": cmd_aup,
    "cmd_chat": cmd_chat,
    "cmd_clean": cmd_clean,
    "cmd_crit": cmd_crit,
    "cmd_gamble": cmd_gamble,
    "cmd_help": cmd_help,
    "cmd_inc": cmd_inc,
    "cmd_incscore": cmd_incscore,
    "cmd_random": cmd_random,
}

__all__ = [
    "LOGIC",
    "cmd_aup",
    "cmd_chat",
    "cmd_clean",
    "cmd_crit",
    "cmd_gamble",
    "cmd_help",
    "cmd_inc",
    "cmd_incscore",
    "cmd_random",
    "duels",
    "logic",
]
