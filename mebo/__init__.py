"""
    Mebo is a python package to control the `Mebo Robot <https://meborobot.com>`_ with Python. 

    .. note::

        This package and the associated modules have been tested on Mebo version 1 *only*.

    .. moduleauthor:: Cameron Lane <crlane@adamanteus.com>


    Installation
    ============

    .. code::
        
        pip install mebo

    Quickstart
    ==========

    .. code::

        >>> from mebo import Mebo
        >>> m = Mebo()
        >>> m.move('N', dur=1000)
"""

__version__ = '0.1.0.dev5'

from .robot import Mebo
from .exceptions import (
    MeboCommandError,
    MeboConfigurationError,
    MeboConnectionError,
    MeboDiscoveryError,
    MeboRequestError,
)

__all__ = [
    'Mebo',
    'MeboCommandError',
    'MeboConfigurationError',
    'MeboConnectionError',
    'MeboDiscoveryError',
    'MeboRequestError',
]
