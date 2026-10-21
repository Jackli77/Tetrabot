"""CONTROLLER layer: the request pipeline behind every invocation.

Controllers are the ONLY code that turns a raw Discord event into a
command run.  Each controller recognises one invocation style, normalises it
into a shared :class:`tetrabot.controllers.context.CommandContext`, and
dispatches to the SAME shared handler — so ``!gamble`` and ``/gamble`` run
the exact same code:

* :mod:`tetrabot.controllers.base` — the shared pipeline every transport
  follows (detect → resolve → authorize → validate → dispatch).
* :mod:`tetrabot.controllers.prefix` — the ``!`` controller: the message
  pipeline (ignore-self → DM/guild routing → prefix parsing).
* :mod:`tetrabot.controllers.slash` — the ``/`` controller: native slash
  tree registration, generated from the command catalog.
* :mod:`tetrabot.controllers.listen` — the listening controller: every
  message of the channel the bot listens to is answered.
* :mod:`tetrabot.controllers.commands` — the shared command handlers.

Controllers never contain business rules and never query the database
directly — they only detect, normalise, and delegate.
"""
from tetrabot.controllers.base import BaseController, DetectionResult
from tetrabot.controllers.context import ChallengeRequest, CommandContext
from tetrabot.controllers.listen import ListenController
from tetrabot.controllers.listen import handle_message as handle_listen_message
from tetrabot.controllers.prefix import PrefixController, handle_message
from tetrabot.controllers.slash import SlashController, setup_slash_commands

__all__ = [
    "BaseController",
    "ChallengeRequest",
    "CommandContext",
    "DetectionResult",
    "ListenController",
    "PrefixController",
    "SlashController",
    "handle_listen_message",
    "handle_message",
    "setup_slash_commands",
]
