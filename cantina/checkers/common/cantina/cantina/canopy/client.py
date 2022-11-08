import asyncio
import logging
import can

from typing import Dict, Optional, Tuple
from functools import partial

from cantina import Cipher
from .fields import ExtraData, Session, MessageLength, SequenceNumber, \
    CipherData
from .messages import SessionStartMessage, SessionDataMessage
from .session import SessionState


class Client:
    def __init__(
        self, 
        cipher: Cipher, 
        send_queue: asyncio.Queue,
        msg_ids: Dict[str, int],
        logger: Optional[logging.Logger] = None
    ):
        self.send_queue = send_queue
        self.cipher = cipher
        self.sessions: Dict[
            Session,
            SessionState
        ] = dict()

        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
        
        # Assign message IDs
        self.mid_start = msg_ids['canopy_start']
        self.mid_data = msg_ids['canopy_data']
        self.mid_reply_start = msg_ids['canopy_reply_start']
        self.mid_reply_data = msg_ids['canopy_reply_data']
    
    def _initialize_session(
        self,
        _: Session,
        state: SessionState
    ) -> None:
        state.cipher = self.cipher

    async def _send_start(
        self,
        session_id: Session,
        state: SessionState,
        length: MessageLength,
        extra_data: ExtraData
    ) -> None:
        msg = SessionStartMessage.encrypt(
            state.cipher,
            session_id,
            length,
            extra_data
        )
        await self.send_queue.put(msg.can_msg(self.mid_start))

    async def _send_data(
        self,
        session_id: Session,
        state: SessionState,
        data: bytes
    ) -> None:
        # Chunk size is leftover of CAN-FD frame size 
        chunk_size = 64 - SessionDataMessage.min_length()
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset:offset + chunk_size]
            msg = SessionDataMessage.encrypt(
                state.cipher,
                session_id,
                SequenceNumber(offset // chunk_size),
                data=chunk
            )
            await self.send_queue.put(msg.can_msg(self.mid_data))

    async def _handle_reply_start(self, can_msg: can.Message) -> None:
        msg = SessionStartMessage.from_msg(can_msg)
        if msg is None:
            # Message was not in expected format for
            # given message ID!
            return

        session = self.sessions.get(msg.session_id)
        if session is None:
            # Not our session (or possible error)
            return
        
        plain_data = msg.decrypt(session.cipher)
        if plain_data is None:
            # If we don't pass the auth check we
            # definitely don't want to send an error,
            # this is most likely malicious activity
            logging.info('InvalidTag for {}'.format(
                msg.session_id
            ))
            return 

        # Store number of bytes to receive in reply
        session.remaining_bytes = msg.length.value
        session.start_data = msg.extra_data.value

    async def _handle_reply_data(self, can_msg: can.Message) -> None:
        msg = SessionDataMessage.from_msg(can_msg)
        if msg is None:
            # Message was not in expected format for
            # given message ID!
            return

        session = self.sessions.get(msg.session_id)
        if session is None:
            # Not our session (or possible error)
            return

        if session.seq != msg.seq:
            # Sequence IDs don't match up
            return
        
        plain_data = msg.decrypt(session.cipher)
        if plain_data is None:
            # If we don't pass the auth check we
            # definitely don't want to send an error,
            # this is most likely malicious activity
            logging.info('InvalidTag for {}'.format(
                msg.session_id
            ))
            return 

        # Check if we still expect enough data
        data_len = len(plain_data)
        if data_len > session.remaining_bytes:
            # I don't think this can technically
            # happen together with the other precautions,
            # but just checking it to be safe
            logging.info('Payload bigger than expected, ' \
                'got {}, expected {}'.format(
                    data_len,
                    session.remaining_bytes
                )
            )
            return

        session.add_data(plain_data)

    async def send(
        self,
        data: bytes,
        session_id: Optional[Session] = None,
        start_data: Optional[bytes] = None
    ) -> Tuple[Optional[bytes], Optional[str]] :
        # STEP 0: Session start
        # -------------------------------------------------------------
        # We generate a random session ID and we need the
        # number of bytes of data we want to send. If a session with
        # the same ID already exists, generate a new ID and try agin
        #
        # We don't encrypt anything here, keep all "flow" info
        # in plaintext and only store the order data later on
        # in the encrypted part. But we're still making use of
        # the AEAD scheme, using AD only.
        #
        # Maximum amount of data we can transmit in a session is
        # 8192, if we have a sequence number of one byte (with
        # the encryption, we can transmit 36 bytes of data, minus
        # what we need for the session_id and sequence number,
        # assuming a 2 byte session ID and 2 byte sequence number)
        state = SessionState()
        if session_id is None:
            session_id = Session()

            # TODO: Race condition!
            while session_id in self.sessions:
                session_id = Session()

        # Initialize state
        if start_data is not None:
            state.start_data = start_data
        self._initialize_session(session_id, state)
        if not state.cipher.ok():
            return None, 'Symmetric key not yet available'
        self.sessions[session_id] = state

        # STEP 1: Wrap the data
        # -------------------------------------------------------------
        # We currently don't have any protection against out of
        # order messages. I don't know if it's *possible* in our
        # case to have out of order messages, but if it is not,
        # we can simply skip this step later on.
        #
        # We're just using an authenticated tag here to later on
        # check, whether the overall data has been transmitted
        # correctly (since we have an auth tag on every message,
        # the only thing that could happen should really only be
        # out-of-order transmission...)
        data += bytes(CipherData.from_plaintext(state.cipher, ad=data))

        # Wrap everything that follows in try, so session gets deleted
        try:
            # Still STEP 1: Send the session start message
            # ---------------------------------------------------------
            if start_data is not None:
                await self._send_start(
                    session_id,
                    state,
                    MessageLength(len(data)),
                    ExtraData(start_data)
                )
            else:
                await self._send_start(
                    session_id,
                    state,
                    MessageLength(len(data)),
                    ExtraData.empty()
                )


            # STEP 2: Send the data across
            # ---------------------------------------------------------
            # For step 2 we're gonna split the data into chunks of 
            # our specified size, tag it with session and sequence
            # id and send it across the bus.
            await self._send_data(session_id, state, data)

            # STEP 3: Wait for response
            # ---------------------------------------------------------
            session = self.sessions[session_id]
            if session is not None:
                await asyncio.wait_for(
                    session.received.wait(),
                    SessionState.SESSION_TIMEOUT / 1_000_000_000
                )
                return bytes(session.buffer), None
            else:
                return None, 'No such client session'
        except asyncio.TimeoutError:
            return None, 'Timeout while waiting for canopy response'
        finally:
            # STEP 4: Cleanup session info
            # ---------------------------------------------------------
            del self.sessions[session_id]

    def recv_handlers(self):
        return {
            self.mid_reply_start: \
                partial(Client._handle_reply_start, self),
            self.mid_reply_data: \
                partial(Client._handle_reply_data, self)
        }

