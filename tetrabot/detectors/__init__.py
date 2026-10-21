"""DETECTORS layer: transport detection for incoming Discord events.

Detectors are the ONLY code that touches Discord transports.  Each detector
recognises one invocation style, normalises it into a shared
:class:`tetrabot.context.CommandContext`, and dispatches to the SAME shared
logic — so ``!gamble`` and ``/gamble`` run the exact same code:

* :mod:`tetrabot.detectors.prefix` — the ``!`` detector: the message pipeline
  (ignore-self → DM/guild routing → prefix parsing).
* :mod:`tetrabot.detectors.slash` — the ``/`` detector: native slash tree
  registration, generated from the command catalog.

Detectors never contain business rules and never query the database
directly — they only detect, normalise, and delegate.
"""
from tetrabot.detectors.base import BaseDetector, DetectionResult
from tetrabot.detectors.prefix import PrefixDetector, handle_message
from tetrabot.detectors.slash import SlashDetector

__all__ = [
    "BaseDetector",
    "DetectionResult",
    "PrefixDetector",
    "SlashDetector",
    "handle_message",
]
