class MeboError(Exception):
    pass


class MeboCommandError(MeboError):
    pass


class MeboRequestError(MeboError):
    pass


class MeboConnectionError(MeboError):
    pass


class MeboDiscoveryError(MeboError):
    pass
