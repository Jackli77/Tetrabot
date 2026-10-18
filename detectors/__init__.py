"""DETECTORS layer: transport detection for incoming Discord events.

Detectors are the ONLY code that touches Discord transports.  Each detector
recognises one invocation style, normalises it into a shared
:class:`controllers.CommandContext`, and dispatches to the SAME
``controllers.LOGIC`` functions — so ``!gamble`` and ``/gamble`` run the
exact same logic:

* :mod:`detectors.prefix` — ``!`` detector: the message pipeline
  (ignore-self → DM/guild routing → prefix parsing) plus the ``!`` command
  adapters (``BaseCommand`` classes + routers).
* :mod:`detectors.slash` — ``/`` detector: native slash tree registration
  plus per-command thin wrappers.

Detectors never contain business rules and never query the database
directly — they only detect, normalise, and delegate to controllers.
"""
from detectors.base import BaseDetector, DetectionResult
from detectors.prefix.detector import PrefixDetector
from detectors.slash.detector import SlashDetector

__all__ = [
    "BaseDetector",
    "DetectionResult",
    "PrefixDetector",
    "SlashDetector",
]
