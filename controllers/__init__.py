"""CONTROLLER layer: transport-agnostic command orchestration.

Each ``cmd_*`` function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Prefix (``!``) and slash (``/``) transports both build a CommandContext and
dispatch through the LOGIC registry, so one implementation serves both.
"""
from controllers.context import CommandContext, make_prefix_respond, make_slash_respond
from controllers.registry import LOGIC

__all__ = ["CommandContext", "make_prefix_respond", "make_slash_respond", "LOGIC"]
