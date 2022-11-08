#!/usr/bin/env python3

import sys
import random
import string
import contextlib

from typing import Callable

from bot_client import BotClient, BotClientException
from client import Client, User
from protocol import Uint64


BOT_USERNAME = 'marketbot'
BOT_UNKNOWN_MSG = "I couldn't understand you! Try /help for a list of commands."

MAX_ITEM_LEN = 100
RECEIPT_SIZE = 88
VIEW_TOKEN_SIZE = 72

USERNAME_LENGTH = 12
PASSWORD_LENGTH = 16


g_tests = []
g_ignore_tests = False


def test(desc: str, only: bool = False):
    def decorator(func: Callable):
        global g_tests, g_ignore_tests
        if only:
            g_tests = [(func, desc)]
            g_ignore_tests = True
        elif not g_ignore_tests:
            g_tests.append((func, desc))
        return func
    return decorator


def randstr(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=length))


def randuser() -> User:
    username = randstr(USERNAME_LENGTH)
    password = randstr(PASSWORD_LENGTH)
    return User(username, password)


def randuser_auth(client: Client) -> User:
    user = randuser()
    client.user = user
    client.register()
    client.auth()
    return user


@contextlib.contextmanager
def expect_exception(exc_type: type, exc_msg: str):
    try:
        yield
    except Exception as e:
        assert isinstance(e, exc_type)
        assert str(e) == exc_msg, f'Got message: {str(e)}'


@test('Bot: parsing')
def bot_parsing(client: Client, bot: BotClient):
    randuser_auth(client)
    cmds = [
        'foobar',
        '/help x',
        '/info x',
        '/sell', '/sell x', '/sell x x', '/sell x 0 foo', '/sell 0 x foo',
        '/buy', '/buy x', '/buy x x', '/buy 0 x',
        '/view', '/view x',
    ]
    for cmd in cmds:
        reply, = bot.chat(cmd)
        assert reply == BOT_UNKNOWN_MSG


@test('Bot: help')
def bot_help(client: Client, bot: BotClient):
    randuser_auth(client)
    bot.help()


@test('Bot: info')
def bot_info(client: Client, bot: BotClient):
    randuser_auth(client)
    user_buyer = client.user
    randuser_auth(client)
    user_seller = client.user

    currency = client.mint(1000000)
    id, _ = bot.sell(1000, currency, 'foobar')

    i_seller, i_price, i_currency, i_receipts = bot.info(id, is_seller=True)
    assert i_seller == user_seller.userid
    assert i_price == 1000
    assert i_currency == currency
    assert len(i_receipts) == 0

    client.user = user_buyer
    i_seller, i_price, i_currency, _ = bot.info(id)
    assert i_seller == user_seller.userid
    assert i_price == 1000
    assert i_currency == currency

    client.user = user_seller
    receipt = client.transfer(user_buyer.userid, currency, 3000)

    client.user = user_buyer
    client.receive(receipt)
    receipts = []
    for _ in range(3):
        receipt = client.transfer(user_seller.userid, currency, 1000)
        bot.buy(id, receipt)
        receipts.append(receipt.dt_encode().hex())

    client.user = user_seller
    _, _, _, i_receipts = bot.info(id, is_seller=True)
    assert i_receipts == receipts


@test('Bot: info error cases')
def bot_info_errors(client: Client, bot: BotClient):
    randuser_auth(client)
    with expect_exception(BotClientException, 'Unexpected reply: Unknown item ID!'):
        bot.info(2**64-1)


@test('Bot: sell error cases')
def bot_sell_errors(client: Client, bot: BotClient):
    randuser_auth(client)
    currency = client.mint(1000000)
    with expect_exception(BotClientException, 'Unexpected reply: Content too long!'):
        bot.sell(1000, currency, 'A'*(MAX_ITEM_LEN+1))


@test('Bot: buy error cases')
def bot_buy_errors(client: Client, bot: BotClient):
    randuser_auth(client)
    user_dummy = client.user

    randuser_auth(client)
    currency = client.mint(1000000)
    id, _ = bot.sell(1000, currency, 'foobar')

    with expect_exception(BotClientException, 'Unexpected reply: Invalid receipt!'):
        receipt = client.transfer(client.user.userid, currency, 1000)
        receipt.amount = Uint64(1000000)
        bot.buy(id, receipt)
    with expect_exception(BotClientException, 'Unexpected reply: Invalid receipt!'):
        receipt = client.transfer(client.user.userid, currency, 1)
        bot.buy(id, receipt)
    with expect_exception(BotClientException, 'Unexpected reply: Invalid receipt!'):
        receipt = client.transfer(
            client.user.userid, client.mint(1000000), 1000)
        bot.buy(id, receipt)
    with expect_exception(BotClientException, 'Unexpected reply: Invalid receipt!'):
        receipt = client.transfer(user_dummy.userid, currency, 1000)
        bot.buy(id, receipt)

    receipt = client.transfer(client.user.userid, currency, 1000)
    receipt_hex = receipt.dt_encode().hex()

    reply, = bot.chat(f'/buy {id} {receipt_hex} 0 a x b 2 c')
    assert reply == 'Invalid position!'
    reply, = bot.chat(f'/buy {id} {receipt_hex} 0 a 1 b 2')
    assert reply == 'Missing character!'
    with expect_exception(BotClientException, 'Unexpected reply: Invalid character!'):
        bot.buy(id, receipt, [(0, 'a'), (1, 'zz'), (2, 'c')])
    with expect_exception(BotClientException, 'Unexpected reply: Repeated position!'):
        bot.buy(id, receipt, [(0, 'a'), (1, 'b'), (1, 'c'), (2, 'd')])
    with expect_exception(BotClientException, 'Unexpected reply: Unknown item ID!'):
        bot.buy(2**64-1, receipt)
    with expect_exception(BotClientException, 'Unexpected reply: Wrong character!'):
        bot.buy(id, receipt, [(0, 'f'), (2, 'X'), (5, 'r')])


@test('Bot: view error cases')
def bot_view_errors(client: Client, bot: BotClient):
    randuser_auth(client)
    with expect_exception(BotClientException, 'Unexpected reply: Invalid view token!'):
        bot.view('00'*VIEW_TOKEN_SIZE)
    # Can't test unknown item ID path without privkey


@test('Bot: sell and view')
def bot_sell_view(client: Client, bot: BotClient):
    randuser_auth(client)
    currency = client.mint(1000000)
    _, token = bot.sell(1000, currency, 'foobar')
    content = bot.view(token)
    assert content == 'foobar'


@test('Bot: sell, buy, and view')
def bot_sell_buy_view(client: Client, bot: BotClient):
    randuser_auth(client)
    currency = client.mint(1000000)
    id, _ = bot.sell(1000, currency, 'foobar')
    receipt = client.transfer(client.user.userid, currency, 1000)
    token = bot.buy(id, receipt)
    content = bot.view(token)
    assert content == 'foobar'


@test('Bot: buy with partial knowledge')
def bot_buy_partial(client: Client, bot: BotClient):
    randuser_auth(client)
    currency = client.mint(1000000)
    id, _ = bot.sell(1000, currency, 'foobar')
    receipt = client.transfer(client.user.userid, currency, 500)
    bot.buy(id, receipt, [(0, 'f'), (3, 'b'), (5, 'r')])


def run_tests(host: str, port: int, bot_uid: int):
    global g_tests

    for func, desc in g_tests:
        print(desc, file=sys.stderr)

        client = Client()
        client.connect(host, port)
        bot = BotClient(client, bot_uid)

        try:
            func(client, bot)
        finally:
            client.close()


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <host> <port>', file=sys.stderr)
        exit(1)

    host, port = sys.argv[1:]
    port = int(port)

    client = Client()
    client.connect(host, port)
    try:
        randuser_auth(client)
        bot_uid = client.get_userid(BOT_USERNAME)
    finally:
        client.close()

    run_tests(host, port, bot_uid)


if __name__ == '__main__':
    main()
