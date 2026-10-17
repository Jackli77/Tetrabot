"""Automatic registry of every ``cmd_*`` controller function."""
from controllers import commands as _commands

LOGIC = {
    name: func
    for name, func in vars(_commands).items()
    if name.startswith("cmd_") and callable(func)
}
