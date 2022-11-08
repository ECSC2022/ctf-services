import time
import struct

from typing import List, Optional, Tuple

from client import Client
from protocol import TransferReceipt


class BotClientException(Exception):
    pass


class BotClient:
    def __init__(self, client: Client, uid: int, read_retries: int = 3):
        self._client = client
        self._uid = uid
        self._read_retries = read_retries
        self._replies = []

    def help(self) -> str:
        reply, = self.chat('/help')
        assert reply == \
            "Welcome to Market Bot! Available commands:\n" \
            "- /help: show this help.\n" \
            "- /info <ID>: show information on item <ID>.\n" \
            "- /sell <price> <currency ID> <content>: list a new item on the " \
            "market.\n" \
            "- /buy <ID> <receipt> [<pos> <char>]...: buy item <ID> with a " \
            "hex-encoded receipt for the transfer of its price to the seller. You " \
            "can get a discount if you already know part of the item: specify one " \
            "or more <pos> <char> to prove you know <char> at position <pos>.\n" \
            "- /view <token>: show item for a view token obtained through /sell " \
            "or /buy."
        return reply

    def info(self, id: int, is_seller: bool = False) -> Tuple[int, int, int, Optional[List[str]]]:
        reply, = self.chat(f'/info {id}')
        prefix = f'--- Item {id} ---\nSeller: '
        if not reply.startswith(prefix):
            raise BotClientException(f'Unexpected reply: {reply}')
        reply = reply[len(prefix):]
        s_seller, reply = reply.split('\n', maxsplit=1)
        seller = int(s_seller)
        assert reply.startswith('Price: ')
        reply = reply[len('Price: '):]
        s_price, reply = reply.split(' ', maxsplit=1)
        price = int(s_price)
        assert reply.startswith('(currency ')
        reply = reply[len('(currency '):]
        s_currency, reply = reply.split(')', maxsplit=1)
        currency = int(s_currency)
        receipts = None
        if is_seller:
            assert reply.startswith('\nSales: ')
            reply = reply[len('\nSales: '):]
            s_sales, reply = reply.split(' ', maxsplit=1)
            sales = int(s_sales)
            assert reply == '(receipts follow)'
            receipt_replies = self.read_replies(sales)
            receipts = []
            for receipt_reply in receipt_replies:
                assert receipt_reply.startswith('Sale transfer receipt: ')
                receipt = receipt_reply[len('Sale transfer receipt: '):]
                receipts.append(receipt)
        return seller, price, currency, receipts

    def sell(self, price: int, currency: int, content: str) -> Tuple[int, str]:
        reply, = self.chat(f'/sell {price} {currency} {content}')
        if not reply.startswith('Created item '):
            raise BotClientException(f'Unexpected reply: {reply}')
        reply = reply[len('Created item '):]
        s_id, reply = reply.split('.', maxsplit=1)
        id = int(s_id)
        assert reply.startswith(' View token: ')
        token = reply[len(' View token: '):]
        return id, token

    def buy(self, id: int, receipt: TransferReceipt, known: List[Tuple[int, str]] = []) -> str:
        receipt_hex = receipt.dt_encode().hex()
        msg = f'/buy {id} {receipt_hex}'
        for pos, char in known:
            msg += f' {pos} {char}'
        reply, = self.chat(msg)
        prefix = f'Bought item {id}. View token: '
        if not reply.startswith(prefix):
            raise BotClientException(f'Unexpected reply: {reply}')
        token = reply[len(prefix):]
        return token

    def view(self, token: str) -> str:
        id, = struct.unpack('<Q', bytes.fromhex(token)[:8])
        reply, = self.chat(f'/view {token}')
        prefix = f'Item {id}: '
        if not reply.startswith(prefix):
            raise BotClientException(f'Unexpected reply: {reply}')
        content = reply[len(prefix):]
        return content

    def chat(self, msg: str, reply_count: int = 1) -> List[str]:
        self._client.chat_send(self._uid, msg)
        return self.read_replies(reply_count)

    def read_replies(self, count: int) -> List[str]:
        retries = 0
        while len(self._replies) < count:
            sender, _, content = self._client.chat_read()
            if content is None:
                if retries == self._read_retries:
                    raise BotClientException('Read retries exceeded')
                retries += 1
                continue
            retries = 0
            if sender == self._uid:
                self._replies.append(content)
        replies = self._replies[:count]
        self._replies = self._replies[count:]
        return replies
