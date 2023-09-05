import struct
from hashlib import sha1
import rsa


def get_byte_array(integer):
    """Return the variable length bytes corresponding to the given int"""
    # Operate in big endian (unlike most of Telegram API) since:
    # > "...pq is a representation of a natural number
    #    (in binary *big endian* format)..."
    # > "...current value of dh_prime equals
    #    (in *big-endian* byte order)..."
    # Reference: https://core.telegram.org/mtproto/auth_key
    return int.to_bytes(
        integer,
        (integer.bit_length() + 8 - 1) // 8,  # 8 bits per byte,
        byteorder='big',
        signed=False
    )


def serialize_bytes(data):
    """Write bytes by using Telegram guidelines"""
    if not isinstance(data, bytes):
        if isinstance(data, str):
            data = data.encode('utf-8')
        else:
            raise TypeError(
                'bytes or str expected, not {}'.format(type(data)))

    r = []
    if len(data) < 254:
        padding = (len(data) + 1) % 4
        if padding != 0:
            padding = 4 - padding

        r.append(bytes([len(data)]))
        r.append(data)

    else:
        padding = len(data) % 4
        if padding != 0:
            padding = 4 - padding

        r.append(bytes([
            254,
            len(data) % 256,
            (len(data) >> 8) % 256,
            (len(data) >> 16) % 256
        ]))
        r.append(data)

    r.append(bytes(padding))
    return b''.join(r)


def _compute_fingerprint(key):
    """
    Given a RSA key, computes its fingerprint like Telegram does.

    :param key: the Crypto.RSA key.
    :return: its 8-bytes-long fingerprint.
    """
    n = serialize_bytes(get_byte_array(key.n))
    e = serialize_bytes(get_byte_array(key.e))
    # Telegram uses the last 8 bytes as the fingerprint
    return struct.unpack('<q', sha1(n + e).digest()[-8:])[0]


def add_key(pub, server_keys, *, old):
    """Adds a new public key to be used when encrypting new data is needed"""
    key = rsa.PublicKey.load_pkcs1(pub)
    server_keys[_compute_fingerprint(key)] = (key, old)
