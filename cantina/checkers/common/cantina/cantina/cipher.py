import secrets

from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag


class Cipher:
    def __init__(self):
        self.cipher = None
        self.cipher_old = None

    def update(self, cipher: ChaCha20Poly1305):
        self.cipher_old = self.cipher
        self.cipher = cipher

    def encrypt(
        self,
        data: bytes = b'',
        ad: Optional[bytes] = None
    ) -> bytes:
        assert self.cipher is not None, \
            'Check cipher is ok before attempting encryption'
        nonce = secrets.token_bytes(12)
        ciphertext = self.cipher.encrypt(nonce, data, ad)
        return nonce + ciphertext

    def decrypt(
        self,
        nonce: bytes,
        ciphertext: bytes,
        ad: Optional[bytes] = None
    ) -> Optional[bytes]:
        if self.cipher is None:
            return None
        try:
            return self.cipher.decrypt(nonce, ciphertext, ad)
        except InvalidTag:
            # Try old cipher
            if self.cipher_old is None:
                return None
            try:
                return self.cipher_old.decrypt(nonce, ciphertext, ad)
            except InvalidTag:
                return None

    def ok(self) -> bool:
        # TODO: could add an out-of-date here?
        return self.cipher is not None
