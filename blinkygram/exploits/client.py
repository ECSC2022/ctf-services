import logging
import ecdsa
import socket

from hashlib import sha256
from typing import List, Tuple, Type

from protocol import *


class ClientException(Exception):
    pass


def generate_key(seed: str = None) -> ecdsa.SigningKey:
    entropy = ecdsa.util.PRNG(seed) if seed is not None else None
    return ecdsa.SigningKey.generate(
        ecdsa.curves.NIST256p, hashfunc=sha256, entropy=entropy)


class User:
    def __init__(self, username: str, password: str,
                 sk: ecdsa.SigningKey = None, auth_token: AuthToken = None):
        if sk is None:
            sk = generate_key()
        self.username = username
        self.password = password
        self.sk = sk
        self.auth_token = auth_token

    @property
    def pubkey(self) -> str:
        return self.sk.get_verifying_key().to_pem().decode()

    @property
    def userid(self) -> int:
        return self.auth_token.userid


class Client:
    def __init__(self, user: User = None, timeout: float = 10.0):
        self.user = user
        self._timeout = timeout
        self._sock = None
        self._seq = 0

    def connect(self, host: str, port: int):
        self._sock = socket.create_connection(
            (host, port), timeout=self._timeout)

    def close(self):
        self._sock.close()
        self._sock = None

    @property
    def connected(self):
        return self._sock is not None

    def echo(self, data: bytes):
        req = RequestMessage(REQUEST_KIND_ECHO, EchoRequest(data))
        reply = self._request(req, EchoReply).reply
        if reply.data != data:
            raise ClientException(
                f'Mismatched echo reply: {reply.data} vs {data}')

    def register(self, exist_ok: bool = False):
        req = RequestMessage(REQUEST_KIND_REGISTER, RegisterRequest(
            self.user.username, self.user.password, self.user.pubkey))
        reply = self._request(req, check=False)
        if reply.status != REPLY_STATUS_OK:
            if not exist_ok or reply.reply != b'User exists':
                raise ClientException(f'Failure reply: {reply}')

    def auth(self):
        req = RequestMessage(REQUEST_KIND_AUTH, AuthRequest(
            self.user.username, self.user.password))
        reply = self._request(req, AuthReply).reply
        self.user.auth_token = reply.token

    def get_userid(self, username: str) -> int:
        req = RequestMessage(REQUEST_KIND_USERID, UseridRequest(
            self.user.auth_token, username))
        reply = self._request(req, UseridReply).reply
        return reply.userid

    def get_username(self, userid: int) -> str:
        req = RequestMessage(REQUEST_KIND_USERNAME, UsernameRequest(
            self.user.auth_token, userid))
        reply = self._request(req, UsernameReply).reply
        return reply.username

    def get_pubkey(self, userid: int) -> str:
        req = RequestMessage(REQUEST_KIND_PUBKEY, PubkeyRequest(
            self.user.auth_token, userid))
        reply = self._request(req, PubkeyReply).reply
        return reply.pubkey

    def chat_send(self, userid: int, content: str):
        req = RequestMessage(REQUEST_KIND_CHAT_SEND, ChatSendRequest(
            self.user.auth_token, userid, content))
        self._request(req)

    def chat_read(self) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        req = RequestMessage(REQUEST_KIND_CHAT_READ, ChatReadRequest(
            self.user.auth_token))
        reply = self._request(req, ChatReadReply, check=False)
        if reply.status != REPLY_STATUS_OK:
            if reply.reply != b'No messages':
                raise ClientException(f'Failure reply: {reply}')
            return None, None, None
        return reply.reply.sender_userid, reply.reply.timestamp, reply.reply.content

    def get_balance(self, currency: int) -> int:
        req = RequestMessage(REQUEST_KIND_BALANCE, BalanceRequest(
            self.user.auth_token, currency))
        reply = self._request(req, BalanceReply).reply
        return reply.balance

    def transfer(self, userid: int, currency: int, amount: int) -> TransferReceipt:
        req = RequestMessage(REQUEST_KIND_TRANSFER, TransferRequest(
            self.user.auth_token, amount, currency, userid))
        reply = self._request(req, TransferReply).reply
        return reply.receipt

    def receive(self, receipt: TransferReceipt):
        req = RequestMessage(REQUEST_KIND_RECEIVE, ReceiveRequest(
            self.user.auth_token, receipt))
        self._request(req)

    def mint(self, amount: int) -> int:
        req = RequestMessage(REQUEST_KIND_MINT, MintRequest(
            self.user.auth_token, amount))
        reply = self._request(req, MintReply).reply
        return reply.currency

    def check_receipt(self, receipt: TransferReceipt):
        req = RequestMessage(REQUEST_KIND_CHECK_RECEIPT, CheckReceiptRequest(
            self.user.auth_token, receipt))
        self._request(req)

    def new_backup(self, data: bytes = bytes()) -> str:
        req = RequestMessage(REQUEST_KIND_NEW_BACKUP, NewBackupRequest(
            self.user.auth_token, data))
        reply = self._request(req, NewBackupReply).reply
        return reply.id

    def get_backup(self, id: str) -> str:
        req = RequestMessage(REQUEST_KIND_GET_BACKUP, GetBackupRequest(
            self.user.auth_token, id))
        reply = self._request(req, GetBackupReply).reply
        return reply.data

    def _request(self, req: RequestMessage, reply_cls: Type[DataType] = None,
                 check=True) -> ReplyMessage:
        req_data = req.dt_encode()
        hdr = MessageHeader(self._seq, len(req_data))
        self._seq += 1
        msg = hdr.dt_encode() + req_data
        self._sock.sendall(msg)

        reply_hdr = MessageHeader.dt_decode(self._recvn(MessageHeader.SIZE))
        if reply_hdr.seq != hdr.seq:
            raise ClientException(
                f'Incorrect sequence number: {reply_hdr.seq} vs {hdr.seq}')
        reply_data = self._recvn(reply_hdr.length)
        reply = ReplyMessage.dt_decode(reply_data, reply_cls)

        if check and reply.status != REPLY_STATUS_OK:
            raise ClientException(f'Failure reply: {reply}')

        return reply

    def _recvn(self, size: int) -> bytes:
        data = b''
        while len(data) < size:
            data += self._sock.recv(size - len(data))
        return data
