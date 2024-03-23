import os

from hashlib import md5


def _hash(s):
    return md5(s).hexdigest()


def _combine(*args, encoding='utf-8'):
    return ':'.join(args).encode('utf-8')


def ha1(username, realm, password=None):
    if password is None:
        password = os.getenv('STREAM_PASSWORD')
    if not password:
        raise Exception('supply stream password')
    return _hash(_combine(username, realm, password))


def ha2(method, uri):
    return _hash(_combine(method, uri))


def challenge_response(nonce, username, realm, password, method, uri):
    """ Calculates the challenge response for digest authentication. Detials are
    available here: https://tools.ietf.org/html/rfc2617

    :param nonce: The server generated nonce issued in the challenge response
    :param username: the username for to be used for digest authentication
    :param realm: The realm (namespace) of the protected information
    :param password: The password used to protect the information
    :param method: The method used for the request (i.e, GET or DESCRIBE, depending on protocol)
    :param uri: THe uri of the requested resource
    >>> nonce = '595ebd874c33ec0efa0aa306077ae6304c4573c7ad70c0b583298ab2ada7e1a6'
    >>> username = 'stream'
    >>> realm = 'realm'
    >>> method = 'DESCRIBE'
    >>> uri = 'rtsp://172.16.1.107/streamhd/ '
    >>> expected_response = '91b3cd804ec214aeaebfcf51306a093a'
    >>> calculated_response = challenge_response(nonce, username, realm, None, method, uri)
    >>> assert calculated_response == expected_response
    """
    h1 = ha1(username, realm, password)
    h2 = ha2(method, uri)
    return _hash(_combine(h1, nonce, h2))
