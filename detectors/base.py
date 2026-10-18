"""DETECTORS layer: base types shared by every detector."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass
class DetectionResult:
    """Normalised outcome of transport detection.

    * ``handled`` — False means "not for us, ignore silently".
    * ``command`` / ``args`` — parsed command name and arguments (``!`` only;
      ``/`` detectors dispatch directly and leave these empty).
    * ``handler`` — the detector-internal entry point chosen for this event
      (``detectors.prefix.router.handle_command`` or
      ``detectors.prefix.dm.router.handle_command``).
    * ``extra`` — free-form flags passed downstream
      (e.g. ``extra["dm"]`` is True for direct messages).
    """

    handled: bool = True
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    handler: Optional[Callable[..., Awaitable]] = None
    extra: dict[str, Any] = field(default_factory=dict)

    # Backwards-compatible alias: filters used ``result.proceed``.
    @property
    def proceed(self) -> bool:
        """Alias for :attr:`handled` (kept for the old filters API)."""
        return self.handled

    @proceed.setter
    def proceed(self, value: bool) -> None:
        self.handled = value


# Backwards-compatible alias: filters used ``FilterResult`` / ``MessageFilter``.
FilterResult = DetectionResult


class MessageFilter:
    """Legacy alias: use :class:`BaseDetector` for new code.

    Kept so the old ``filters`` API (``FilterResult``/``MessageFilter`` with
    ``apply(message, bot, result)``) still imports.  New detectors subclass
    :class:`BaseDetector` and implement :meth:`detect`.
    """

    async def apply(self, message, bot_client, result: DetectionResult) -> DetectionResult:
        """Inspect ``message`` and update ``result``.  Must be overridden."""
        raise NotImplementedError  # To be defined by every filter


class BaseDetector:
    """Base class for every detector.

    Subclasses recognise one invocation style (``!`` messages, ``/``
    interactions) and delegate to the shared controller logic.
    """

    name: str = "base"

    async def detect(self, event, bot_client) -> DetectionResult:
        """Inspect ``event``; return a result with ``handled=False`` when
        the event is not for this detector."""
        raise NotImplementedError  # To be defined by every detector
