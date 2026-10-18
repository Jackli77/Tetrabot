"""CONTROLLER layer: transport-agnostic command orchestration.

Each ``cmd_*`` function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Prefix (``!``) and slash (``/``) transports both build a CommandContext and
dispatch through the LOGIC registry, so one implementation serves both.

Subpackages:

* ``controllers.commands`` — the shared ``cmd_*`` business logic.
* ``controllers.prefix`` — ``!`` transport (BaseCommand classes + router).
* ``controllers.dm`` — private-message ``!`` transport (BaseDm + router).
* ``controllers.slash`` — native ``/`` transport (Discord command tree).
"""
from controllers.context import CommandContext, make_prefix_respond, make_slash_respond
from controllers.registry import LOGIC

__all__ = ["CommandContext", "make_prefix_respond", "make_slash_respond", "LOGIC"]

