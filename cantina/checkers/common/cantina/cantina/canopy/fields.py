import abc
import secrets
import struct

from dataclasses import dataclass
from typing import Optional, ClassVar, TypeVar, Type, Tuple, Generic

from cantina import Cipher


_Value = TypeVar('_Value')
_CanopyField = TypeVar('_CanopyField', bound='CanopyField')
@dataclass(frozen=True)
class CanopyField(abc.ABC, Generic[_Value]):
    FIELD_SIZE: ClassVar[int]
    PACKING: ClassVar[str]
    value: Type[_Value]

    def __new__(cls, *_, **__):
        if cls == CanopyField:
            raise TypeError('Cannot instantiate abstract class.')
        return super().__new__(cls)

    @classmethod
    def _value_valid(
        cls: Type[_CanopyField],
        _: Type[_Value]
    ) -> bool:
        return True
    
    @classmethod
    def _value_from_bytes(
        cls: Type[_CanopyField],
        b: bytes
    ) -> _Value:
        return struct.unpack(cls.PACKING, b)[0]

    def __bytes__(self):
        return struct.pack(self.PACKING, self.value)

    @classmethod
    def from_bytes(
        cls: Type[_CanopyField], 
        b: bytes
    ) -> Tuple[Optional[_CanopyField], int]:
        if len(b) < cls.FIELD_SIZE:
            return None, 0

        v = cls._value_from_bytes(b[:cls.FIELD_SIZE])
        if not cls._value_valid(v):
            return None, 0

        return cls(v), cls.FIELD_SIZE


@dataclass(frozen=True)
class Session(CanopyField[int]):
    FIELD_SIZE: ClassVar[int] = 4
    PACKING: ClassVar[str] = '>I'
    value: int

    def __init__(self, value: Optional[int] = None):
        if value is None:
            id_bytes = secrets.token_bytes(Session.FIELD_SIZE)
            value = Session._value_from_bytes(id_bytes)
        object.__setattr__(self, 'value', value)


_MessageLength = TypeVar('_MessageLength', bound='MessageLength')
@dataclass(frozen=True)
class MessageLength(CanopyField[int]):
    FIELD_SIZE: ClassVar[int] = 2
    PACKING: ClassVar[str] = '>H'
    MAX_SIZE: ClassVar[int] = 7900
    value: int

    def __init__(self, value: int):
        assert value < MessageLength.MAX_SIZE, \
            'Message must not exceed length'
        object.__setattr__(self, 'value', value)

    @classmethod
    def _value_valid(
        cls: Type[_MessageLength],
        value: int 
    ) -> bool:
        return value < cls.MAX_SIZE


_SequenceNumber = TypeVar('_SequenceNumber', bound='SequenceNumber')
@dataclass(frozen=True)
class SequenceNumber(CanopyField[int]):
    FIELD_SIZE: ClassVar[int] = 1
    PACKING: ClassVar[str] = '>B'
    MAX_SIZE: ClassVar[int] = 256
    value: int

    def __init__(self, value: int):
        assert value < SequenceNumber.MAX_SIZE, \
            'Sequence number has to fit into 1 byte'
        object.__setattr__(self, 'value', value)

    @classmethod
    def _value_valid(
        cls: Type[_SequenceNumber],
        value: int 
    ) -> bool:
        return value < cls.MAX_SIZE


@dataclass(frozen=True)
class ExtraData(CanopyField[bytes]):
    FIELD_SIZE: ClassVar[int] = 30
    PACKING: ClassVar[str] = ''
    value: bytes

    def __init__(self, value: bytes):
        assert len(value) == ExtraData.FIELD_SIZE, \
            'ExtraData needs 30 bytes'
        object.__setattr__(self, 'value', value)

    def __bytes__(self):
        return self.value

    @classmethod
    def from_bytes(
        cls: Type[_CanopyField], 
        b: bytes
    ) -> Tuple[Optional[_CanopyField], int]:
        if len(b) < cls.FIELD_SIZE:
            return None, 0

        # Consume the complete rest of the bytes
        return cls(b[:cls.FIELD_SIZE]), cls.FIELD_SIZE

    @classmethod
    def empty(cls: Type[_CanopyField]) -> _CanopyField:
        return cls(bytes(cls.FIELD_SIZE))


@dataclass(frozen=True)
class CipherData(CanopyField[bytes]):
    # Minimum size for AEAD: 12 byte nonce, 16 byte tag = 28 byte
    FIELD_SIZE: ClassVar[int] = 28
    PACKING: ClassVar[str] = ''
    value: bytes

    def __init__(self, value: bytes):
        assert len(value) >= CipherData.FIELD_SIZE, \
            'CipherData needs at least 28 bytes'
        object.__setattr__(self, 'value', value)

    def __bytes__(self):
        return self.value

    @classmethod
    def from_bytes(
        cls: Type[_CanopyField], 
        b: bytes
    ) -> Tuple[Optional[_CanopyField], int]:
        if len(b) < cls.FIELD_SIZE:
            return None, 0

        # Consume the complete rest of the bytes
        return cls(b), len(b)

    @classmethod
    def empty(cls: Type[_CanopyField]) -> _CanopyField:
        return cls(bytes(cls.FIELD_SIZE))

    @classmethod
    def from_plaintext(
        cls: Type[_CanopyField],
        cipher: Cipher,
        plaintext: bytes = b'',
        ad: Optional[bytes] = None
    ) -> _CanopyField:
        return cls(cipher.encrypt(plaintext, ad))

    def to_plaintext(
        self,
        cipher: Cipher,
        ad: Optional[bytes] = None
    ) -> Optional[bytes]:
        nonce = self.value[:12]
        ct = self.value[12:]
        return cipher.decrypt(nonce, ct, ad)

