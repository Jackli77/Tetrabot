"""DETECTOR/``!``: prefix invocation handling for guild messages and DMs.

* :mod:`detectors.prefix.detector` — :class:`PrefixDetector` recognises
  ``!command args`` in messages and :func:`handle_message` dispatches them.
* :mod:`detectors.prefix.router` — guild ``!`` adapters (``COMMAND_HANDLERS``).
* :mod:`detectors.prefix.dm` — DM ``!`` adapters (``DMS_HANDLERS``).

Every adapter builds a shared :class:`controllers.CommandContext` and calls
the same ``controllers.LOGIC`` functions the ``/`` detector uses, so one
implementation serves both transports.
"""
from detectors.prefix.base_command import BaseCommand
from detectors.prefix.detector import PrefixDetector, handle_message

__all__ = ["BaseCommand", "PrefixDetector", "handle_message"]
