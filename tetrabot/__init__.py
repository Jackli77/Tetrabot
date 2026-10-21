"""Tetrabot — a modular Discord bot.

The package is organised in layers, each with a single responsibility:

* :mod:`tetrabot.config` — settings and constants.
* :mod:`tetrabot.catalog` — the declarative description of every command.
* :mod:`tetrabot.context` — the transport-agnostic command context.
* :mod:`tetrabot.detectors` — the ``!`` and ``/`` transports.
* :mod:`tetrabot.commands` — the shared command logic.
* :mod:`tetrabot.models` — data access and domain rules.
* :mod:`tetrabot.views` — rendering and interactive widgets.
* :mod:`tetrabot.app` — the bot factory and entry point.
"""
__version__ = "1.0.0"

__all__ = ["__version__"]
