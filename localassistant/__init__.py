"""__init__ of the package."""

from localassistant.models import LocasAgent, LocasDocs
from localassistant.qt_gui.app import LocasApp

__all__ = [
    "LocasAgent",
    "LocasDocs",
    "LocasApp"
]

__version__ = '2.0.0rc1'
