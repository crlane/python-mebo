"""Exceptions for the mebo robot"""
class MeboError(Exception):
    """General Error for Mebo"""


class MeboCommandError(MeboError):
    """Exception raised when a command is incorrect"""


class MeboRequestError(MeboError):
    """Exception raised when a request is not accepted by Mebo command server"""


class MeboConnectionError(MeboError):
    """Exception raised when connection to mebo fails"""


class MeboConfigurationError(MeboError):
    """Exception raised when a Mebo misconfiguration is detected"""


class MeboDiscoveryError(MeboError):
    """Exception raised when unable to autodiscover mebo on the LAN"""
