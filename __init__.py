from .core.connection import ComLinkConnection
from .exceptions import ComLinkError, ComLinkTimeout, ComLinkCRCError

from .core.commands.ping import PingCommand
from .core.commands.millis import MillisCommand

__version__ = "1.0.0"
__all__ = [
    "ComLinkConnection",
    "ComLinkError",
    "ComLinkTimeout",
    "ComLinkCRCError",

    "PingCommand",
    "MillisCommand",
]
