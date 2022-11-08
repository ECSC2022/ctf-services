import can

from dataclasses import dataclass, fields
from typing import Optional, TypeVar, Type

from cantina import Cipher
from .fields import CanopyField, ExtraData, Session, SequenceNumber, \
        MessageLength, CipherData


_SessionMessage = TypeVar('_SessionMessage', bound='SessionMessage')
@dataclass(frozen=True)
class SessionMessage:
    def can_msg(self, arbitration_id: int) -> can.Message:
        # Add all attributes
        payload = bytearray()
        for field in fields(self):
            payload += bytes(getattr(self, field.name))

        return can.Message(
            arbitration_id=arbitration_id,
            data=payload,
            is_fd=True,
            is_extended_id=False
        )

    @classmethod
    def min_length(cls: Type[_SessionMessage]):
        length = 0 
        for field in fields(cls):
            length += field.type.FIELD_SIZE
        return length

    @classmethod
    def from_msg(
        cls: Type[_SessionMessage],
        msg: can.Message
    ) -> Optional[_SessionMessage]:
        data = bytes(msg.data)
        kwargs = dict()

        for field in fields(cls):
            if not issubclass(field.type, CanopyField):
                continue

            value, num_bytes = field.type.from_bytes(data)
            if value is None:
                return None

            kwargs[field.name] = value
            data = data[num_bytes:]

        return cls(**kwargs)

    @classmethod
    def encrypt(
        cls: Type[_SessionMessage],
        cipher: Cipher,
        *args,
        data: bytes = b''
    ) -> _SessionMessage:
        kwargs = dict()

        # Find cipher data attribute
        cname: Optional[str] = None
        for field in fields(cls):
            if field.type == CipherData:
                cname = field.name
                break
        assert cname is not None, "No CipherData field found"

        # Add all attributes
        ad = bytearray()
        for arg, field in zip(args, fields(cls)):
            assert isinstance(arg, field.type), "Invalid Argument"
            kwargs[field.name] = arg
            ad += bytes(arg)

        # Encrypt
        ad = bytes(ad)
        cd = CipherData.from_plaintext(cipher, data, ad)
        kwargs[cname] = cd
        return cls(**kwargs)

    def decrypt(self, cipher: Cipher) -> Optional[bytes]:
        cipher_data: Optional[CipherData] = None

        # Build authenticated data for check
        ad = bytearray()
        for field in fields(self):
            if field.type == CipherData:
                cipher_data = getattr(self, field.name)
                continue
            ad += bytes(getattr(self, field.name))

        # If no cipher data was found, we can't decrypt
        if cipher_data is None:
            return None

        return cipher_data.to_plaintext(cipher, bytes(ad))


@dataclass(frozen=True)
class SessionStartMessage(SessionMessage):
    session_id: Session
    length: MessageLength
    extra_data: ExtraData
    cipher_data: CipherData


@dataclass(frozen=True)
class SessionDataMessage(SessionMessage):
    session_id: Session
    seq: SequenceNumber
    cipher_data: CipherData

