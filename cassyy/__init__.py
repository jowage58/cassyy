"""
Simple Apereo Central Authentication Service (CAS) client
"""

import logging as _logging

from .core import (
    AsyncCASClient,
    CASClient,
    CASError,
    CASInvalidServiceError,
    CASInvalidTicketError,
    CASUser,
)

__version__ = "0.0.9"

__all__ = [
    "AsyncCASClient",
    "CASClient",
    "CASError",
    "CASInvalidServiceError",
    "CASInvalidTicketError",
    "CASUser",
]

_logging.getLogger(__name__).addHandler(_logging.NullHandler())
