"""FILTERS layer: base types shared by every message filter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass
class FilterResult:
    """Accumulator threaded through the :class:`FilterPipeline`.

    * ``proceed`` — False stops the pipeline (message is ignored).
    * ``command`` / ``args`` — parsed command name and arguments.
    * ``handler`` — the controller entry point chosen for this message
      (``controllers.prefix.router.handle_command`` or
      ``controllers.dm.router.handle_command``).
    * ``extra`` — free-form flags filters want to pass downstream
      (e.g. ``extra["dm"]`` is True for direct messages).
    """

    proceed: bool = True
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    handler: Optional[Callable[..., Awaitable]] = None
    extra: dict[str, Any] = field(default_factory=dict)


class MessageFilter:
    """Base class for every message filter.

    Subclasses override :meth:`apply`, mutate the given ``result`` and
    return it.  Setting ``result.proceed = False`` stops the pipeline.
    """

    async def apply(self, message, bot_client, result: FilterResult) -> FilterResult:
        """Inspect ``message`` and update ``result``.  Must be overridden."""
        raise NotImplementedError  # To be defined by every filter
