"""DETECTOR/``/``: native slash invocation handling.

:class:`SlashDetector` registers the ``/`` tree; every command builds a
shared :class:`controllers.CommandContext` and calls the same
``controllers.LOGIC`` functions the ``!`` detector uses.
"""
from detectors.slash.detector import SlashDetector, build_context, setup_slash_commands

__all__ = ["SlashDetector", "build_context", "setup_slash_commands"]
