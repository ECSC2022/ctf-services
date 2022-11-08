import abc
import struct
import functools
import dataclasses

from typing import Optional, Type, Union


SIGNATURE_SIZE = 64

MAX_MESSAGE_LEN = 8192

REQUEST_KIND_ECHO = 0x00
REQUEST_KIND_REGISTER = 0x01
REQUEST_KIND_AUTH = 0x02
REQUEST_KIND_USERID = 0x03
REQUEST_KIND_USERNAME = 0x04
REQUEST_KIND_PUBKEY = 0x05
REQUEST_KIND_CHAT_SEND = 0x06
REQUEST_KIND_CHAT_READ = 0x07
REQUEST_KIND_BALANCE = 0x08
REQUEST_KIND_TRANSFER = 0x09
REQUEST_KIND_RECEIVE = 0x0a
REQUEST_KIND_MINT = 0x0b
REQUEST_KIND_CHECK_RECEIPT = 0x0c
REQUEST_KIND_NEW_BACKUP = 0x0d
REQUEST_KIND_GET_BACKUP = 0x0e

REPLY_STATUS_OK = 0x00
REPLY_STATUS_FAIL = 0x01


class ProtocolException(Exception):
    pass


class DataType(abc.ABC):
    @abc.abstractmethod
    def dt_encode(self) -> bytes:
        pass

    def dt_validate(self):
        pass

    @property
    def dt_wire_size(self):
        return len(self.dt_encode())

    @staticmethod
    @abc.abstractmethod
    def dt_decode(bs: bytes) -> 'DataType':
        pass


def Integer(fmt: str):
    class T(int, DataType):
        def dt_encode(self) -> bytes:
            return struct.pack(fmt, self)

        @staticmethod
        def dt_decode(bs: bytes) -> 'T':
            size = len(struct.pack(fmt, 0))
            if len(bs) < size:
                raise RuntimeError('Not enough data')
            value, = struct.unpack(fmt, bs[:size])
            return T(value)

    return T


Uint8 = Integer('<B')
Uint32 = Integer('<I')
Uint64 = Integer('<Q')
Int64 = Integer('<q')


def RawBytes(size: int = None):
    class T(bytes, DataType):
        def dt_encode(self) -> bytes:
            if size is not None and len(self) != size:
                raise ProtocolException('Incorrect size')
            return self

        @staticmethod
        def dt_decode(bs: bytes) -> 'T':
            if size is not None:
                if len(bs) < size:
                    raise ProtocolException('Not enough data')
                bs = bs[:size]
            return T(bs)

    return T


class Bytes(bytes, DataType):
    def dt_encode(self) -> bytes:
        return Uint32(len(self)).dt_encode() + self

    @staticmethod
    def dt_decode(bs: bytes) -> 'Bytes':
        length = Uint32.dt_decode(bs)
        bs = bs[length.dt_wire_size:]
        if length > len(bs):
            raise ProtocolException('Not enough data')
        return Bytes(bs[:length])


class String(str, DataType):
    def dt_encode(self) -> bytes:
        return Bytes(self.encode()).dt_encode()

    @staticmethod
    def dt_decode(bs: bytes) -> 'String':
        bs = Bytes.dt_decode(bs)
        if any(b == 0x00 or b > 0x7f for b in bs):
            raise ProtocolException('Invalid characters in string')
        return String(bs.decode())


def Struct(cls):
    @functools.wraps(cls, updated=[])
    class T(dataclasses.dataclass(cls), DataType):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in dataclasses.fields(T):
                value = getattr(self, field.name)
                if not isinstance(value, field.type):
                    setattr(self, field.name, field.type(value))

        def dt_encode(self) -> bytes:
            bs = b''
            for field in dataclasses.fields(T):
                value = getattr(self, field.name)
                bs += value.dt_encode()
            return bs

        def dt_validate(self):
            for field in dataclasses.fields(T):
                getattr(self, field.name).dt_validate()
            super().dt_validate()

        @staticmethod
        def dt_decode(bs: bytes) -> 'T':
            values = {}
            for field in dataclasses.fields(T):
                value = field.type.dt_decode(bs)
                values[field.name] = value
                bs = bs[value.dt_wire_size:]
            st = T(**values)
            st.dt_validate()
            return st

    return T


@Struct
class MessageHeader:
    seq: Uint32
    length: Uint32

    SIZE = 8

    def dt_validate(self):
        if self.length > MAX_MESSAGE_LEN:
            raise ProtocolException('Message too large')


request_kind_map = {}


def request_kind(kind: int):
    def decorator(cls):
        assert kind not in request_kind_map
        request_kind_map[kind] = cls
        return cls
    return decorator


@dataclasses.dataclass
class RequestMessage(DataType):
    kind: int
    req: DataType

    def dt_encode(self) -> bytes:
        return Uint8(self.kind).dt_encode() + self.req.dt_encode()

    @staticmethod
    def dt_decode(bs: bytes) -> 'RequestMessage':
        kind = Uint8.dt_decode(bs)
        bs = bs[kind.dt_wire_size:]
        try:
            cls = request_kind_map[kind]
        except KeyError:
            raise ProtocolException('Unknown request kind')
        return RequestMessage(kind, cls.dt_decode(bs))


@dataclasses.dataclass
class ReplyMessage(DataType):
    status: int
    reply: Optional[DataType] = None

    def dt_encode(self) -> bytes:
        return Uint8(self.status).dt_encode() + self.reply.dt_encode()

    @staticmethod
    def dt_decode(bs: bytes, reply_cls: Type[DataType] = None) -> 'ReplyMessage':
        status = Uint8.dt_decode(bs)
        bs = bs[status.dt_wire_size:]
        if status == REPLY_STATUS_OK and reply_cls is not None:
            reply = reply_cls.dt_decode(bs)
        else:
            reply = RawBytes().dt_decode(bs)
        return ReplyMessage(status, reply)

    @staticmethod
    def ok(reply: DataType = None):
        if reply is None:
            reply = RawBytes()(b'')
        return ReplyMessage(REPLY_STATUS_OK, reply)

    @staticmethod
    def fail(msg: Union[str, bytes]):
        if isinstance(msg, str):
            msg = msg.encode()
        return ReplyMessage(REPLY_STATUS_FAIL, RawBytes()(msg))


@request_kind(REQUEST_KIND_ECHO)
@Struct
class EchoRequest:
    data: RawBytes()


@Struct
class EchoReply:
    data: RawBytes()


@request_kind(REQUEST_KIND_REGISTER)
@Struct
class RegisterRequest:
    username: String
    password: String
    pubkey: String


@Struct
class AuthToken:
    userid: Uint64
    signature: RawBytes(SIGNATURE_SIZE)

    @property
    def signed_data(self):
        return self.dt_encode()[:-SIGNATURE_SIZE]


@request_kind(REQUEST_KIND_AUTH)
@Struct
class AuthRequest:
    username: String
    password: String


@Struct
class AuthReply:
    token: AuthToken


@Struct
class Authenticated:
    auth_token: AuthToken


@request_kind(REQUEST_KIND_USERID)
@Struct
class UseridRequest(Authenticated):
    username: String


@Struct
class UseridReply:
    userid: Uint64


@request_kind(REQUEST_KIND_USERNAME)
@Struct
class UsernameRequest(Authenticated):
    userid: Uint64


@Struct
class UsernameReply:
    username: String


@request_kind(REQUEST_KIND_PUBKEY)
@Struct
class PubkeyRequest(Authenticated):
    userid: Uint64


@Struct
class PubkeyReply:
    pubkey: String


@request_kind(REQUEST_KIND_CHAT_SEND)
@Struct
class ChatSendRequest(Authenticated):
    recipient_userid: Uint64
    content: String


@request_kind(REQUEST_KIND_CHAT_READ)
@Struct
class ChatReadRequest(Authenticated):
    pass


@Struct
class ChatReadReply:
    sender_userid: Uint64
    timestamp: Uint64
    content: String


@request_kind(REQUEST_KIND_BALANCE)
@Struct
class BalanceRequest(Authenticated):
    currency: Uint64


@Struct
class BalanceReply:
    balance: Uint64


@Struct
class TransferReceipt:
    amount: Int64
    currency: Uint64
    recipient_userid: Uint64
    signature: RawBytes(SIGNATURE_SIZE)

    @property
    def signed_data(self):
        return self.dt_encode()[:-SIGNATURE_SIZE]


@request_kind(REQUEST_KIND_TRANSFER)
@Struct
class TransferRequest(Authenticated):
    amount: Int64
    currency: Uint64
    recipient_userid: Uint64


@Struct
class TransferReply:
    receipt: TransferReceipt


@request_kind(REQUEST_KIND_CHECK_RECEIPT)
@Struct
class CheckReceiptRequest(Authenticated):
    receipt: TransferReceipt


@request_kind(REQUEST_KIND_RECEIVE)
@Struct
class ReceiveRequest(Authenticated):
    receipt: TransferReceipt


@request_kind(REQUEST_KIND_MINT)
@Struct
class MintRequest(Authenticated):
    amount: Uint64


@Struct
class MintReply:
    currency: Uint64


@request_kind(REQUEST_KIND_NEW_BACKUP)
@Struct
class NewBackupRequest(Authenticated):
    data: Bytes


@Struct
class NewBackupReply:
    id: String


@request_kind(REQUEST_KIND_GET_BACKUP)
@Struct
class GetBackupRequest(Authenticated):
    id: String


@Struct
class GetBackupReply:
    data: Bytes
