import asyncio
import logging
import secrets
import can

from functools import partial
from typing import Dict, Optional

# Key Exchange imports
from hashlib import blake2s
from hmac import compare_digest
from cryptography.hazmat.primitives.asymmetric.x25519 \
    import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 \
    import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization \
    import Encoding, PublicFormat
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305

from cantina import Cipher


KEYSERVER_REKEY_WAIT = 2 # seconds
KEYSERVER_REKEY_INTERVAL = 10 - KEYSERVER_REKEY_WAIT # seconds


class KeyExchangeServer:
    def __init__(
        self,
        cipher: Cipher,
        send_queue: asyncio.Queue,
        msg_ids: Dict[str, int],
        logger: Optional[logging.Logger] = None
    ):
        """
        Generate keypairs and shared symmetric key on startup
        """
        self.cipher = cipher
        self.send_queue = send_queue
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        # Generate shared symmetric key
        self.symmetric_key = ChaCha20Poly1305.generate_key()

        # Generate a keypair for static ECDH
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.public_key_bytes = self.public_key.public_bytes(
            Encoding.Raw,
            PublicFormat.Raw
        )

        # Derive signing key for PoW token creation
        self.signing_key = Ed25519PrivateKey.generate()
        self.signing_public = self.signing_key.public_key()
        self.signing_public_bytes = self.signing_public.public_bytes(
            Encoding.Raw,
            PublicFormat.Raw
        )

        # Assign message IDs
        self.mid_pubkey = msg_ids['MSGID_KEY_EXCH_PUBKEY_BROADCAST']
        self.mid_rekey = msg_ids['MSGID_KEY_EXCH_REKEY_NOTIFY']
        self.mid_symmetric = msg_ids['MSGID_KEY_EXCH_SHARE_SYMMETRIC']
        self.mid_pubkey_req = msg_ids['MSGID_KEY_EXCH_REQUEST_PUBKEY']
        self.mid_symmetric_req = {
            mid: mtype
            for mtype, mid
            in msg_ids.items()
            if mtype.startswith('MSGID_KEY_EXCH_REQ_')
        }
        self.mid_rekey_req = {
            mid: mtype
            for mtype, mid
            in msg_ids.items()
            if mtype.startswith('MSGID_KEY_EXCH_SYMM_')
        }

    async def update_loop(self) -> None:
        while True:
            await asyncio.sleep(KEYSERVER_REKEY_INTERVAL)
            
            # New symmetric key
            self.symmetric_key = ChaCha20Poly1305.generate_key()
            await self._send_rekey()

            # Update own cipher after rekey notification
            # Wait a bit for everyone to perform the rekey, they
            # should still be able to decipher old messages
            self.cipher.update(ChaCha20Poly1305(self.symmetric_key))

    def sign_data(self, data: bytes) -> bytes:
        return self.signing_key.sign(data)

    def derive_shared_secret(self, public_bytes: bytes) -> bytes:
        # Derive shared key through key exchange
        # Keysize for ChaCha20Poly1305 is 32 bytes
        peer_pubkey = X25519PublicKey.from_public_bytes(public_bytes)
        shared_key = self.private_key.exchange(peer_pubkey)
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'keyserver-exch'
        ).derive(shared_key)

    async def _send_rekey(self) -> None:
        msg = can.Message(
            arbitration_id=self.mid_rekey,
            data=self.public_key_bytes + self.signing_public_bytes,
            is_fd=True,
            is_extended_id=False
        )

        await self.send_queue.put(msg)
        self.logger.info(f'Sent rekey notification')

    async def _send_pubkey(self) -> None:
        """
        Send out the public key on the bus
        NOTE: bus needs to support CAN-FD
        """

        msg = can.Message(
            arbitration_id=self.mid_pubkey,
            data=self.public_key_bytes + self.signing_public_bytes,
            is_fd=True,
            is_extended_id=False
        )

        await self.send_queue.put(msg)
        self.logger.info(f'Sent pubkey broadcast')

    async def _send_symmetric(
        self,
        peer_msg: can.Message,
        send_pubkey: bool = True
    ) -> None:
        """
        A peer sent us (hopefully) a public key, so we're gonna
        respond with our pubkey (for now we're just broadcasting it,
        not sure if we can reduce the number of pubkey messages?)
        and send an authenticated encrypted message with the
        shared symmetric key.
        """

        # Before we broadcast the pubkey, check if the message is
        # somewhat sane first.
        # TODO: Validate message ID at a different place?
        key = bytes(peer_msg.data[:32])
        key_hash = bytes(peer_msg.data[32:])
        if len(peer_msg.data) != 64:
            self.logger.warning('Received message with invalid length')
            return
        if not compare_digest(blake2s(key).digest(), key_hash):
            # Invalid hash, random message?
            self.logger.warning(
                    'Received peer message with invalid hash'
            )
            return

        # Setup cipher and encrypt the shared symmetric key
        derived_key = self.derive_shared_secret(key)
        cipher = ChaCha20Poly1305(derived_key)
        nonce = secrets.token_bytes(12)
        ct = cipher.encrypt(nonce, self.symmetric_key, None)

        # Send pubkey first
        if send_pubkey:
            await self._send_pubkey()

        # Send encrypted message
        msg = can.Message(
            arbitration_id=self.mid_symmetric,
            data=nonce + ct,
            is_fd=True,
            is_extended_id=False
        )

        await self.send_queue.put(msg)
        self.logger.info(f'Sent shared key to peer')

    async def _recv_pubkey_req(self, msg: can.Message) -> None:
        if len(msg.data) == 0:
            await self._send_pubkey()

    async def _recv_symmetric_req(self, msg: can.Message) -> None:
        await self._send_symmetric(msg)

    async def _recv_rekey_req(self, msg: can.Message) -> None:
        await self._send_symmetric(msg, False)

    def recv_handlers(self):
        handlers = {
            self.mid_pubkey_req: partial(
                KeyExchangeServer._recv_pubkey_req,
                self
            )
        }

        # Key exchange listeners
        for mid in self.mid_symmetric_req:
            handlers[mid] = partial(
                KeyExchangeServer._recv_symmetric_req,
                self
            )

        # Rekeying listeners
        for mid in self.mid_rekey_req:
            handlers[mid] = partial(
                KeyExchangeServer._recv_rekey_req,
                self
            )

        return handlers

