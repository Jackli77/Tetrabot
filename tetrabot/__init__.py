"""Tetrabot — a modular Discord bot.

The package follows the MVC pattern, with a shared command catalog on top:

* :mod:`tetrabot.models` — the MODEL layer: data access and domain rules.
* :mod:`tetrabot.views` — the VIEW layer: rendering, widgets, output adapters.
* :mod:`tetrabot.controllers` — the CONTROLLER layer: the request pipeline
  and the shared command handlers.
* :mod:`tetrabot.catalog` — the declarative description of every command,
  the single source of truth shared by both transports.
* :mod:`tetrabot.config` — settings and constants.
* :mod:`tetrabot.app` — the bot factory and entry point.
"""
__version__ = "1.0.0"

__all__ = ["__version__"]
