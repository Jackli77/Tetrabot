"""Tetrabot entry point — delegates to :mod:`config.start`."""
from config.start import create_bot, main

if __name__ == "__main__":
    main()

__all__ = ["create_bot", "main"]

