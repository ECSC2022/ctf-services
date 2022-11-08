#!/bin/env python3

from os import urandom
from hashlib import sha256
from base64 import b64encode

def crack(salt, suffix):
    seq = b''
    while not sha256(salt + seq).digest().endswith(suffix):
        seq = urandom(8)
    return b64encode(seq)

# example
print(crack(b'\xbd\xc8\x1a\x0b\r\x04\x93\x08', b'\xc2\xb5\xaf'))