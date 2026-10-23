"""Entry point — run with ``python -m tetrabot``.

With no argument the Discord bot starts.  ``python -m tetrabot demo``,
``chat``, ``eval`` and ``tools`` run the agent from the terminal instead.
"""
from tetrabot.app import create_bot
from tetrabot.app import main as run_bot
from tetrabot.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["create_bot", "main", "run_bot"]
