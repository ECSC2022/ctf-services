import asyncio
import logging
import can

from functools import partial
from typing import Dict, Optional

# Key Exchange imports
from hashlib import blake2s
from cryptography.hazmat.primitives.asymmetric.x25519 \
    import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.serialization \
    import Encoding, PublicFormat
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag

# CANtina
from cantina import Cipher


class KeyExchange:
    def __init__(
        self,
        cipher: Cipher,
        send_queue: asyncio.Queue,
        msg_ids: Dict[str, int],
        logger: Optional[logging.Logger] = None
    ):
        """
        Generate keypairs for key exchange.
        """
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.public_key_bytes = self.public_key.public_bytes(
            Encoding.Raw,
            PublicFormat.Raw
        )
        self.derived_key: Optional[bytes] = None
        self.cipher = cipher
        self.send_queue = send_queue
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        # Assign message IDs
        self.mid_recv_pubkey = msg_ids['recv_pubkey'] 
        self.mid_recv_symm = msg_ids['recv_symm']
        self.mid_recv_rekey = msg_ids['recv_rekey']
        self.mid_request = msg_ids['request']

    async def update_loop(self) -> None:
        while True:
            await asyncio.sleep(1)

            if self.derived_key is None or not self.cipher.ok():
                await self._send_pubkey()

    async def _send_pubkey(self) -> None:
        # Request the public key from the keyserver
        public_key_digest = blake2s(self.public_key_bytes) \
            .digest()
        msg = can.Message(
            arbitration_id=self.mid_request,
            data=self.public_key_bytes + public_key_digest,
            is_extended_id=False,
            is_fd=True
        )
        await self.send_queue.put(msg)

    async def _recv_keyserver_public_key(
        self,
        peer_msg: can.Message
    ) -> None:
        if len(peer_msg.data) != 64:
            return

        key = bytes(peer_msg.data[:32])
        key = X25519PublicKey.from_public_bytes(key)

        # Derive shared key through key exchange
        # Keysize for ChaCha20Poly1305 is 32 bytes
        shared_key = self.private_key.exchange(key)
        self.derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'keyserver-exch'
        ).derive(shared_key)

    async def _recv_symmetric_key(
        self,
        peer_msg: can.Message
    ) -> None:
        # We haven't established a derived key yet
        if self.derived_key is None:
            return

        # TODO: Check server data for sanity
        if len(peer_msg.data) != 60:
            return
        nonce = bytes(peer_msg.data[:12])
        ct = bytes(peer_msg.data[12:])

        # Setup cipher and decrypt the shared symmetric key
        cipher = ChaCha20Poly1305(self.derived_key)
        try:
            symmetric_key = cipher.decrypt(nonce, ct, None)
        except InvalidTag:
            return
        self.cipher.update(ChaCha20Poly1305(symmetric_key))

        self.logger.info('Shared key updated.')

    async def _recv_rekey_notify(
        self,
        peer_msg: can.Message
    ) -> None:
        await self._recv_keyserver_public_key(peer_msg)
        await self._send_pubkey()

    def recv_handlers(self):
        return {
            self.mid_recv_pubkey: \
                partial(KeyExchange._recv_keyserver_public_key, self),
            self.mid_recv_symm: \
                partial(KeyExchange._recv_symmetric_key, self),
            self.mid_recv_rekey: \
                partial(KeyExchange._recv_rekey_notify, self)
        }
