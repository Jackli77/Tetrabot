"""CONTROLLER layer: transport-agnostic command orchestration.

Each ``cmd_*`` function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Two detectors feed this shared logic — :mod:`detectors.prefix` (``!``) and
:mod:`detectors.slash` (``/``) — so one implementation serves both.  This
package stays detector-free: it only exposes the context, the ``cmd_*``
implementations, and the ``LOGIC`` registry.
"""
from controllers.context import CommandContext, make_prefix_respond, make_slash_respond
from controllers.registry import LOGIC

__all__ = ["CommandContext", "make_prefix_respond", "make_slash_respond", "LOGIC"]

