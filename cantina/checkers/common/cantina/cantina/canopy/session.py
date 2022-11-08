import asyncio
import time

from dataclasses import dataclass, field
from typing import Optional, ClassVar

from .fields import SequenceNumber
from ..cipher import Cipher


@dataclass
class SessionState:
    SESSION_TIMEOUT: ClassVar[int] = 2_000_000_000 # 2s

    remaining_bytes: int = 0
    received: asyncio.Event = \
        field(default_factory=lambda: asyncio.Event())
    response: bytes = b''
    last_checked: int = 0
    start_data: bytes = b''
    seq: SequenceNumber = \
        field(default_factory=lambda: SequenceNumber(0))
    buffer: bytearray = \
        field(default_factory=lambda: bytearray())
    cipher: Cipher = \
        field(default_factory=lambda: Cipher())

    def __post_init__(self):
        self.refresh()

    def refresh(self):
        """
        Update the internal timestamp with nanoseconds precision
        """
        self.last_checked = time.monotonic_ns()

    def is_timeout(self) -> bool:
        """
        Check if this session timed out (i.e. hasn't been refreshed
        within a specified interval)
        """
        ntime = time.monotonic_ns()
        return ntime - self.last_checked > self.SESSION_TIMEOUT

    def add_data(self, data: bytes) -> Optional[bytearray]:
        self.seq = SequenceNumber(self.seq.value + 1)
        self.buffer += data
        self.remaining_bytes -= len(data)
        if self.remaining_bytes > 0:
            return None

        # We're done, return data
        self.received.set()
        return self.buffer
