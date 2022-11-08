#!/usr/bin/env python3

import struct
import random
import logging

from typing import Tuple

from bot_client import BotClient
from checker_rand import RandomScheduler
from checker_util import randstr, randuser_auth, ExceptionContext, ServiceChecker

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


CHECKER_ENTROPY_SECRET_SEED = '6CjMlTfykpwL1kLijkF3'

BOT_USERNAME = 'marketbot'

# We must ensure that the flag price is high enough to make it impossible for
# players to buy it by guessing characters. At the same time, we don't want it
# to be too high, to reduce the amount of double-spends required to buy it
# through the ECDSA malleability bug.
# Flags are 37 characters long, where 5 characters are a fixed prefix and the
# rest is base64-encoded information and signature. The entropy comes entirely
# from the HMAC, which is 80 bits (see https://github.com/fausecteam/ctf-gameserver/blob/faustctf-2021/doc/source/flags.rst).
# Assuming a (excessive) 30 minute flag expiration, and (excessive) 100 requests
# per second, we will assume players can guess another log2(60*30*100) = 18 bits
# of entropy. Therefore, we must ensure the flag cannot be bought by guessing
# all except 80-18 = 62 bits. Once base64-encoded, they are 10 characters
# (rounding down as that adds extra security margin), so we must ensure the
# flag cannot be bought by guessing all but 10 characters.
# Let I be the initial balance of a user, and K an unreasonable number of users
# required to pool together their initial balances. Let P be the flag price.
# We get:
# 10/37 * P >= K * I  =>  P = 3.7 * K * I
# Let D be the number of double-spends required to reach P. Then:
# D = log2(P / I) = log2(3.7 * K)
# Since D does not depend on I, we can choose the initial balance to avoid
# integer overflow issues in discount (src/bot/chat.c:handle_buy). We treat
# amounts as 64-bit signed integer to avoid breakage due to the protocol
# signedness bug. The worst-case calculation is 37 * P, therefore we require:
# 37 * P < 2**63  =>  P < 2**63 / 37 = 249280325320399346
# Final equations and constraints:
# P = 3.7 * K * I
# D = log2(3.7 * K)
# P < 249280325320399346
# Under the previous considerations, we will assume players can register,
# authenticate, transfer and receive 60*30*100/4 = 45000 times, and choose
# K = 50000 conservatively.
# For I = 10, we get P = 1850000 and D = 18. We can pick P <= 2621440 without
# increasing D. With some security margin, we pick P in [1900000, 2600000].
FLAG_PRICE_MIN = 1900000
FLAG_PRICE_MAX = 2600000

# 5 ticks, 20x safety factor
FLAG_LIFE = 100

MINT_MIN = FLAG_LIFE * FLAG_PRICE_MAX
MINT_MAX = 10 * MINT_MIN

assert MINT_MAX < 2**63-1


class Checker(ServiceChecker):
    checks = RandomScheduler()

    def __init__(self, ip: str, team: int):
        super().__init__(self.checks, ip, team)
        self._users = None
        self._bot_uid = None
        self._minter = None
        self._seller = None
        self._buyer = None
        self._mint_amount = None
        self._currency = None
        self._amount_m2b = None
        self._receipt_m2b = None
        self._item_id = None
        self._item_price = None
        self._item_content = None
        self._sell_token = None
        self._receipt_b2s = None
        self._buy_token = None
        self._num_known = None
        self._receipt_b2s_partial = None
        self._buy_token_partial = None

    def _place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        random.seed(CHECKER_ENTROPY_SECRET_SEED + flag)
        with ExceptionContext('failed to register seller', result=CheckResult.FLAG_NOT_FOUND):
            randuser_auth(self._client)
        price = random.randint(FLAG_PRICE_MIN, FLAG_PRICE_MAX)
        mint_amount = random.randint(MINT_MIN, MINT_MAX)

        self._rand_reconnect()

        with ExceptionContext('failed to get bot user ID', result=CheckResult.FLAG_NOT_FOUND):
            bot_uid = self._client.get_userid(BOT_USERNAME)
        self._rand_reconnect()
        bot = BotClient(self._client, bot_uid)

        with ExceptionContext('failed to mint', result=CheckResult.FLAG_NOT_FOUND):
            currency = self._client.mint(mint_amount)
        self._rand_reconnect()

        with ExceptionContext('failed to sell item', result=CheckResult.FLAG_NOT_FOUND):
            item_id, _ = bot.sell(price, currency, flag)

        checkerlib.set_flagid(f'item:{item_id}')

        return CheckResult.OK, ''

    def _check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)

        if not flagid:
            logging.info('No flagid saved for this team and tick')
            return CheckResult.FLAG_NOT_FOUND, 'flag was not placed successfully'

        item_id = int(flagid[len('item:'):])

        random.seed(CHECKER_ENTROPY_SECRET_SEED + flag)
        with ExceptionContext('failed to auth as seller', result=CheckResult.FLAG_NOT_FOUND):
            seller_user = randuser_auth(self._client)
        price = random.randint(FLAG_PRICE_MIN, FLAG_PRICE_MAX)
        mint_amount = random.randint(MINT_MIN, MINT_MAX)

        self._rand_reconnect()

        with ExceptionContext('failed to get bot user ID', result=CheckResult.FLAG_NOT_FOUND):
            bot_uid = self._client.get_userid(BOT_USERNAME)
        self._rand_reconnect()
        bot = BotClient(self._client, bot_uid)

        random.seed()
        with ExceptionContext('failed to register buyer', result=CheckResult.FLAG_NOT_FOUND):
            buyer_user = randuser_auth(self._client)
        self._rand_reconnect()
        with ExceptionContext('failed to get item info', result=CheckResult.FLAG_NOT_FOUND):
            _, _, currency, _ = bot.info(item_id)
        self._rand_reconnect()
        with ExceptionContext('failed to transfer to buyer', result=CheckResult.FLAG_NOT_FOUND):
            self._client.user = seller_user
            buyer_balance = random.randint(price, mint_amount // FLAG_LIFE)
            receipt = self._client.transfer(
                buyer_user.userid, currency, buyer_balance)
        self._rand_reconnect()
        with ExceptionContext('failed to receive transfer', result=CheckResult.FLAG_NOT_FOUND):
            self._client.user = buyer_user
            self._client.receive(receipt)
        self._rand_reconnect()
        with ExceptionContext('failed to transfer to seller', result=CheckResult.FLAG_NOT_FOUND):
            amount = random.randint(price, buyer_balance)
            receipt = self._client.transfer(
                seller_user.userid, currency, amount)
        self._rand_reconnect()

        with ExceptionContext('failed to buy item', result=CheckResult.FLAG_NOT_FOUND):
            token = bot.buy(item_id, receipt)
        self._rand_reconnect()
        with ExceptionContext('failed to view item', result=CheckResult.FLAG_NOT_FOUND):
            content = bot.view(token)

        if content != flag:
            return CheckResult.FLAG_NOT_FOUND, 'incorrect flag returned'

        return CheckResult.OK, ''

    @checks.task('create_users')
    @ExceptionContext('user creation failed')
    def checks_create_users(self) -> Tuple[CheckResult, str]:
        self._users = []
        for _ in range(3):
            user = randuser_auth(self._client)
            self._users.append(user)
        random.shuffle(self._users)
        self._minter, self._buyer, self._seller = self._users
        return CheckResult.OK, ''

    @checks.task('mint', 'create_users')
    @ExceptionContext('mint failed')
    def checks_mint(self) -> Tuple[CheckResult, str]:
        self._client.user = self._minter
        self._mint_amount = random.randint(MINT_MIN, MINT_MAX)
        self._currency = self._client.mint(self._mint_amount)
        return CheckResult.OK, ''

    @checks.task('transfer_m2b', 'mint')
    @ExceptionContext('transfer to buyer failed')
    def checks_transfer_m2b(self) -> Tuple[CheckResult, str]:
        self._client.user = self._minter
        self._amount_m2b = random.randint(MINT_MIN, self._mint_amount)
        self._receipt_m2b = self._client.transfer(
            self._buyer.userid, self._currency, self._amount_m2b)
        return CheckResult.OK, ''

    @checks.task('receive_buyer', 'transfer_m2b')
    @ExceptionContext('receive from buyer failed')
    def checks_receive_buyer(self) -> Tuple[CheckResult, str]:
        self._client.user = self._buyer
        self._client.receive(self._receipt_m2b)
        return CheckResult.OK, ''

    @checks.task('bot_uid', 'create_users')
    @ExceptionContext('get bot user ID failed')
    def checks_bot_uid(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        self._bot_uid = self._client.get_userid(BOT_USERNAME)
        return CheckResult.OK, ''

    @checks.task('help', 'bot_uid', prob=0.3)
    @ExceptionContext('help failed')
    def checks_help(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        bot = BotClient(self._client, self._bot_uid)
        bot.help()
        return CheckResult.OK, ''

    @checks.task('sell', 'bot_uid', 'mint')
    @ExceptionContext('sell failed')
    def checks_sell(self) -> Tuple[CheckResult, str]:
        self._client.user = self._seller
        bot = BotClient(self._client, self._bot_uid)
        self._item_price = random.randint(FLAG_PRICE_MIN, FLAG_PRICE_MAX)
        self._item_content = randstr(37)
        self._item_id, self._sell_token = bot.sell(
            self._item_price, self._currency, self._item_content)
        with ExceptionContext('malformed view token from sell'):
            self._check_view_token(self._sell_token, self._item_id)
        return CheckResult.OK, ''

    @checks.task('info', 'sell')
    @ExceptionContext('info failed')
    def checks_info(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice([self._minter, self._buyer])
        bot = BotClient(self._client, self._bot_uid)
        seller, price, currency, _ = bot.info(self._item_id)
        if seller != self._seller.userid:
            return CheckResult.FAULTY, 'incorrect item seller'
        if price != self._item_price:
            return CheckResult.FAULTY, 'incorrect item price'
        if currency != self._currency:
            return CheckResult.FAULTY, 'incorrect currency'
        return CheckResult.OK, ''

    @checks.task('transfer_b2s', 'receive_buyer', 'sell')
    @ExceptionContext('transfer to seller failed')
    def checks_transfer_b2s(self) -> Tuple[CheckResult, str]:
        self._client.user = self._buyer
        # Leave enough balance for partial buy
        amount = random.randint(
            self._item_price, self._amount_m2b - self._item_price)
        self._receipt_b2s = self._client.transfer(
            self._seller.userid, self._currency, amount)
        return CheckResult.OK, ''

    @checks.task('buy', 'transfer_b2s')
    @ExceptionContext('buy failed')
    def checks_buy(self) -> Tuple[CheckResult, str]:
        self._client.user = self._buyer
        bot = BotClient(self._client, self._bot_uid)
        self._buy_token = bot.buy(self._item_id, self._receipt_b2s)
        with ExceptionContext('malformed view token from buy'):
            self._check_view_token(self._buy_token, self._item_id)
        return CheckResult.OK, ''

    @checks.task('view_sell', 'sell')
    @ExceptionContext('view after selling failed')
    def checks_view_sell(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        bot = BotClient(self._client, self._bot_uid)
        content = bot.view(self._sell_token)
        if content != self._item_content:
            return CheckResult.FAULTY, 'incorrect item content'
        return CheckResult.OK, ''

    @checks.task('view_buy', 'buy')
    @ExceptionContext('view after buying failed')
    def checks_view_buy(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        bot = BotClient(self._client, self._bot_uid)
        content = bot.view(self._buy_token)
        if content != self._item_content:
            return CheckResult.FAULTY, 'incorrect item content'
        return CheckResult.OK, ''

    @checks.task('transfer_b2s_partial', 'receive_buyer', 'sell', prob=0.5)
    @ExceptionContext('transfer to seller for partial buy failed')
    def checks_transfer_b2s_partial(self) -> Tuple[CheckResult, str]:
        self._client.user = self._buyer
        self._num_known = random.randint(0, len(self._item_content))
        amount = self._item_price * \
            (len(self._item_content) - self._num_known) // len(self._item_content)
        self._receipt_b2s_partial = self._client.transfer(
            self._seller.userid, self._currency, amount)
        return CheckResult.OK, ''

    @checks.task('buy_partial', 'transfer_b2s_partial')
    @ExceptionContext('partial buy failed')
    def checks_buy_partial(self) -> Tuple[CheckResult, str]:
        self._client.user = self._buyer
        bot = BotClient(self._client, self._bot_uid)
        known = random.sample(
            list(enumerate(self._item_content)), self._num_known)
        self._buy_token_partial = bot.buy(
            self._item_id, self._receipt_b2s_partial, known)
        with ExceptionContext('malformed view token from partial buy'):
            self._check_view_token(self._buy_token_partial, self._item_id)
        return CheckResult.OK, ''

    @checks.task('view_buy_partial', 'buy_partial')
    @ExceptionContext('view after partial buy failed')
    def checks_view_buy_partial(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        bot = BotClient(self._client, self._bot_uid)
        content = bot.view(self._buy_token_partial)
        if content != self._item_content:
            return CheckResult.FAULTY, 'incorrect item content'
        return CheckResult.OK, ''

    @checks.task('info_seller', 'buy', 'buy_partial')
    @ExceptionContext('info from seller failed')
    def checks_info_seller(self) -> Tuple[CheckResult, str]:
        self._client.user = self._seller
        bot = BotClient(self._client, self._bot_uid)
        seller, price, currency, receipts = bot.info(
            self._item_id, is_seller=True)
        if seller != self._seller.userid:
            return CheckResult.FAULTY, 'incorrect item seller'
        if price != self._item_price:
            return CheckResult.FAULTY, 'incorrect item price'
        if currency != self._currency:
            return CheckResult.FAULTY, 'incorrect currency'
        b2s_hex = self._receipt_b2s.dt_encode().hex()
        b2s_partial_hex = self._receipt_b2s_partial.dt_encode().hex()
        receipts = set(receipts)
        if len(receipts) != 2:
            return CheckResult.FAULTY, 'incorrect number of seller receipts'
        if b2s_hex not in receipts or b2s_partial_hex not in receipts:
            return CheckResult.FAULTY, 'incorrect seller receipts'
        return CheckResult.OK, ''

    def _check_view_token(self, token: str, item_id: int):
        bs = bytes.fromhex(token)
        assert len(bs) == 8+64
        token_item_id, = struct.unpack('<Q', bs[:8])
        assert token_item_id == item_id


if __name__ == '__main__':
    checkerlib.run_check(Checker)
