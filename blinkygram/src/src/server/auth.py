import ecdsa
import struct

from hashlib import sha256
from typing import Optional

from protocol import SIGNATURE_SIZE, AuthToken, TransferReceipt


class Authenticator:
    def __init__(self, sign_key: ecdsa.SigningKey):
        self._sk = sign_key
        self._vk = sign_key.get_verifying_key()

    def make_token(self, userid: int) -> AuthToken:
        token = AuthToken(userid, b'\x00' * SIGNATURE_SIZE)
        sig = self._sk.sign(token.signed_data)
        assert len(sig) == SIGNATURE_SIZE
        return AuthToken(userid, sig)

    def check_token(self, token: AuthToken) -> bool:
        return self._verify(token.signature, token.signed_data)

    def make_receipt(self, amount: int, currency: int, recipient: int) -> TransferReceipt:
        receipt = TransferReceipt(
            amount, currency, recipient, b'\x00' * SIGNATURE_SIZE)
        sig = self._sk.sign(receipt.signed_data)
        assert len(sig) == SIGNATURE_SIZE
        return TransferReceipt(amount, currency, recipient, sig)

    def check_receipt(self, receipt: TransferReceipt) -> bool:
        return self._verify(receipt.signature, receipt.signed_data)

    def _verify(self, sig: bytes, data: bytes) -> bool:
        try:
            return self._vk.verify(sig, data)
        except ecdsa.BadSignatureError:
            return False

    @staticmethod
    def from_path(path: str):
        try:
            with open(path) as f:
                sk = ecdsa.SigningKey.from_pem(f.read(), hashfunc=sha256)
        except FileNotFoundError:
            sk = ecdsa.SigningKey.generate(
                ecdsa.curves.NIST256p, hashfunc=sha256)
            with open(path, 'wb') as f:
                f.write(sk.to_pem())
        return Authenticator(sk)


def deserialize_pubkey(pubkey: str) -> Optional[ecdsa.VerifyingKey]:
    return ecdsa.VerifyingKey.from_pem(pubkey, hashfunc=sha256)
