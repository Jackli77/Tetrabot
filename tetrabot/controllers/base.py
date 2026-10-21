"""The base controller — the shared request pipeline.

A *controller* turns a raw Discord event into a **command request** and runs
it.  The pipeline is the same for every transport:

    detect -> resolve (catalog) -> authorize (scope) -> validate ->
    build the request -> run the shared handler

Only *detect* and *build the request* are transport specific; everything
else lives here, so ``!gamble`` and ``/gamble`` follow exactly the same
path through the application.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from tetrabot.controllers.commands import HANDLERS
from tetrabot.controllers.context import CommandContext

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Normalised outcome of transport detection.

    * ``handled`` — False means "not for us, ignore silently".
    * ``command`` / ``args`` — the parsed command name and arguments.
    * ``is_dm`` — True when the event came from a private message.
    * ``extra`` — free-form flags passed downstream.
    """

    handled: bool = True
    command: str | None = None
    args: list[str] = field(default_factory=list)
    is_dm: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class BaseController:
    """Base class of every transport controller.

    Subclasses recognise one invocation style and delegate to the shared
    command handlers.
    """

    name: str = "base"

    # -- transport specific steps --------------------------------------

    async def detect(self, event, bot_client) -> DetectionResult:
        """Inspect ``event``; return a result with ``handled=False`` when
        the event is not for this controller."""
        raise NotImplementedError

    def build_context(self, spec, result, event, bot_client) -> CommandContext:
        """Build the normalised request out of a detected invocation."""
        raise NotImplementedError

    # -- shared steps ---------------------------------------------------

    def is_available(self, spec, result) -> bool:
        """Whether the command may run in the context of the invocation.

        The default allows everything; the prefix controller narrows it down
        with the scope declared in the catalog.
        """
        return True

    async def validate(self, spec, result, event, bot_client) -> bool:
        """Check the invocation before running it.

        Returning ``False`` stops the command; the controller may report the
        problem to the user on the way out.
        """
        return True

    async def dispatch(self, spec, result, event, bot_client) -> None:
        """Run a resolved command through the shared pipeline."""
        if not self.is_available(spec, result):
            return
        if not await self.validate(spec, result, event, bot_client):
            return
        ctx = self.build_context(spec, result, event, bot_client)
        await self.execute(spec, ctx)

    async def execute(self, spec, ctx) -> None:
        """Call the shared handler registered for this command."""
        handler = HANDLERS.get(spec.handler)
        if handler is None:
            logger.error("No handler registered for %s", spec.handler)
            return
        await handler(ctx)


__all__ = ["BaseController", "DetectionResult"]
