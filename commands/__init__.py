from os import listdir
from os.path import dirname, basename


# Automatically import every class inside the commands package.
# Scans the directory for all .py files (excluding __init__.py) and
# builds __all__ so that `from commands import *` loads every command module.
__all__ = [basename(f)[:-3] for f in listdir(dirname(__file__)) if f[-3:] == ".py" and not f.endswith("__init__.py")]