"""DETECTOR/``!``/DM: ``!`` command adapters for private messages."""
from detectors.prefix.dm.base_dm import BaseDm
from detectors.prefix.dm.commands import Commands
from detectors.prefix.dm.hot import hot

__all__ = ["BaseDm", "Commands", "hot"]
