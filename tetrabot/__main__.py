"""Entry point — run with ``python -m tetrabot``."""
from tetrabot.app import create_bot, main

if __name__ == "__main__":
    main()

__all__ = ["create_bot", "main"]
