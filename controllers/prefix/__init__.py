"""CONTROLLERS/prefix: metadata + dispatch for ``!`` commands.

Defines the :class:`BaseCommand` transport adapter and re-exports every
prefix command module so :mod:`controllers.prefix.router` (and
``controllers.commands.cmd_help``) sees them.  Command behaviour itself
lives once in ``controllers/commands.py`` and is shared with ``/``.
"""
from controllers.prefix.aup import aup
from controllers.prefix.base_command import BaseCommand
from controllers.prefix.clean import Clean
from controllers.prefix.commands import Commands
from controllers.prefix.crit import crit
from controllers.prefix.gamble import gamble
from controllers.prefix.inc import inc
from controllers.prefix.incscore import incscore
from controllers.prefix.random import Random

__all__ = [
    "BaseCommand",
    "aup",
    "Clean",
    "Commands",
    "crit",
    "gamble",
    "inc",
    "incscore",
    "Random",
]
