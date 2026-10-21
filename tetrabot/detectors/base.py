"""Shared detector types.

A *detector* recognises one invocation style (``!`` messages, ``/``
interactions) and normalises it into a shared
:class:`tetrabot.context.CommandContext`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


class BaseDetector:
    """Base class for every detector.

    Subclasses recognise one invocation style and delegate to the shared
    command logic.
    """

    name: str = "base"

    async def detect(self, event, bot_client) -> DetectionResult:
        """Inspect ``event``; return a result with ``handled=False`` when
        the event is not for this detector."""
        raise NotImplementedError


__all__ = ["BaseDetector", "DetectionResult"]
