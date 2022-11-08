import asyncio
import logging
import can

from typing import Dict, Optional
from functools import partial

from cantina import Cipher
from .fields import Session, CipherData, MessageLength, \
    SequenceNumber
from .messages import SessionStartMessage, SessionDataMessage
from .session import SessionState


class Server:
    def __init__(
        self,
        cipher: Cipher,
        send_queue: asyncio.Queue,
        msg_ids: Dict[str, int],
        logger: Optional[logging.Logger] = None
    ):
        self.cipher = cipher
        self.send_queue = send_queue
        self.sessions: Dict[Session, SessionState] = dict()
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        # Assign message IDs
        self.mid_start = msg_ids['canopy_start']
        self.mid_data = msg_ids['canopy_data']
        self.mid_reply_start = msg_ids['canopy_reply_start']
        self.mid_reply_data = msg_ids['canopy_reply_data']

    async def _send_reply_start(
        self,
        session_id: Session,
        session_state: SessionState,
        length: MessageLength
    ) -> None:
        msg = SessionStartMessage.encrypt(
            session_state.cipher,
            session_id,
            length 
        )
        await self.send_queue.put(msg.can_msg(self.mid_reply_start))

    async def _send_reply_data(
        self,
        session_id: Session,
        session_state: SessionState,
        data: bytes
    ) -> None:
        # Chunk size is leftover of CAN-FD frame size 
        chunk_size = 64 - SessionDataMessage.min_length()
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset:offset + chunk_size]
            msg = SessionDataMessage.encrypt(
                session_state.cipher,
                session_id,
                SequenceNumber(offset // chunk_size),
                data=chunk
            )
            await self.send_queue.put(msg.can_msg(self.mid_reply_data))

    async def build_reply(
        self,
        _: Session,
        __: bytes) -> bytes:
        """
        Send empty reply per default, subclass server
        to overwrite.
        """
        return b''

    async def update_loop(self) -> None:
        while True:
            await asyncio.sleep(1)

            # Remove stale sessions from session state dict
            # TODO: locking!
            stale_sessions = [
                session_id
                for session_id, state in self.sessions.items()
                if state.is_timeout()
            ]
            for session_id in stale_sessions:
                self.logger.info(f'Session {session_id} timed out')
                del self.sessions[session_id]

    def _initialize_session(
        self,
        _: Session,
        state: SessionState
    ) -> None:
        state.cipher = self.cipher

    async def _handle_session_start(self, can_msg: can.Message):
        # STEP 1: Received session start
        # -------------------------------------------------
        # We received a session start packet, before we
        # verify the integrity, check if we already have
        # an open session with the same ID.
        #
        # If we don't have an open session, verify the
        # integrity, then create the session structure
        # in our session table.
        msg = SessionStartMessage.from_msg(can_msg)
        if msg is None:
            # Message was not in expected format for
            # given message ID!
            return

        self.logger.info(f'Received session start: {msg}')
        if msg.session_id in self.sessions:
            # Session already exists!
            self.logger.info('Session {} exists!'.format(
                msg.session_id
            ))
            return
        
        # Initialize the session state
        state = SessionState(msg.length.value)
        self._initialize_session(msg.session_id, state)

        # Try if we can decrypt the message
        if msg.decrypt(state.cipher) is None:
            # If we don't pass the auth check we
            # definitely don't want to send an error,
            # this is most likely malicious activity
            self.logger.info('InvalidTag for {}'.format(
                msg.session_id
            ))
            return 

        # Parse the rest of the message
        # TODO: locking!
        self.sessions[msg.session_id] = state
        self.logger.info('{} started, {}'.format(
            msg.session_id,
            msg.length
        ))

    async def _handle_session_data(self, can_msg: can.Message):
        # STEP 2: Receive the data frames from a peer
        # -------------------------------------------------
        # Now we're receiving the data frames from the
        # peer, hopefully in order. We're checking the
        # order by only accepting frames that correspond
        # the to correct sequence ID
        msg = SessionDataMessage.from_msg(can_msg)
        if msg is None:
            # Message was not in expected format for given message ID!
            return

        self.logger.info(f'Received session data: {msg}')
        state = self.sessions.get(msg.session_id)
        if state is None:
            # No such session! We can't accept the data in this case
            self.logger.info('No such {}!'.format(
                msg.session_id
            ))
            return

        # Make sure sequence IDs match up 
        if state.seq != msg.seq:
            self.logger.info(
                'Expected {}, got {} for {}'.format(
                    state.seq,
                    msg.seq,
                    msg.session_id 
                )
            )
            return

        # Decrypt frame
        plain_data = msg.decrypt(state.cipher)
        if plain_data is None:
            # If we don't pass the auth check we
            # definitely don't want to send an error,
            # this is most likely malicious activity
            self.logger.info('InvalidTag for {}, {}'.format(
                msg.session_id, msg.seq
            ))
            return

        # Check if we still expect enough data
        data_len = len(plain_data)
        if data_len > state.remaining_bytes:
            # I don't think this can technically
            # happen together with the other precautions,
            # but just checking it to be safe
            self.logger.info('Payload bigger than expected, ' \
                'got {}, expected {}'.format(
                    data_len,
                    state.remaining_bytes
                )
            )
            return

        # If we get something non-None here, we're done
        # receiving
        payload = state.add_data(plain_data)
        if payload is None:
            state.refresh()
            return

        # Remove state from session table
        # TODO: locking!
        del self.sessions[msg.session_id]

        # Make sure payload was sent in order (
        # in theory our sequence number check should
        # have already taken care of that)
        payload = bytes(payload)
        data = payload[:-CipherData.FIELD_SIZE]
        cd = CipherData(payload[-CipherData.FIELD_SIZE:])
        if cd.to_plaintext(state.cipher, data) is None:
            # If we don't pass the auth check we
            # definitely don't want to send an error,
            # this is most likely malicious activity
            self.logger.info('InvalidTag for assembled {}'.format(
                msg.session_id
            ))
            return

        # Now we just need to respond to this..
        self.logger.info(f'Received data: {data.hex()}')

        # Build reply and send it back
        data = await self.build_reply(msg.session_id, data)
        await self._send_reply_start(
            msg.session_id,
            state,
            MessageLength(len(data))
        )
        await self._send_reply_data(msg.session_id, state, data)

    def recv_handlers(self):
        return {
            self.mid_start: \
                partial(Server._handle_session_start, self),
            self.mid_data: \
                partial(Server._handle_session_data, self)
        }

