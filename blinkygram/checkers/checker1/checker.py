#!/usr/bin/env python3

import io
import logging
import random
import time
import zipfile

from checker_rand import RandomScheduler
from checker_util import randstr, randuser, ExceptionContext, ServiceChecker, randuser_auth
from protocol import MAX_MESSAGE_LEN

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult
from typing import Tuple


CHECKER_ENTROPY_SECRET_SEED = 'Rwq0finAR1RAjd9cllKI'

BOT_USERNAME = 'marketbot'

SET_PHRASES = [
    'sir this is a family restaurant',
    'I want a refund',
    'thats rude',
    'hello',
    'hey',
    'wow',
    'lorem ipsum'
]


def set_tick_seed(flag: str, key: str):
    random.seed(flag + key + CHECKER_ENTROPY_SECRET_SEED)


def get_tick_randlambda(flag: str, key: str, f):
    set_tick_seed(flag, key)
    return f()


def get_tick_randuser(flag: str, key: str):
    return get_tick_randlambda(flag, key, lambda: randuser())


def get_tick_randuser_auth(flag: str, key: str, client):
    return get_tick_randlambda(flag, key, lambda: randuser_auth(client))


def check_backup(client, backup_id, flag) -> Tuple[CheckResult, str]:
    with ExceptionContext('failed to get backup', result=CheckResult.FLAG_NOT_FOUND):
        backup_content = client.get_backup(backup_id)

    if len(backup_content) > MAX_MESSAGE_LEN:
        return CheckResult.FLAG_NOT_FOUND, 'backup too big'

    backup_io = io.BytesIO(backup_content)
    backup_zip = zipfile.ZipFile(backup_io)

    for info in backup_zip.infolist():
        if info.file_size > MAX_MESSAGE_LEN:
            return CheckResult.FLAG_NOT_FOUND, 'backup component too big'
        if info.filename == 'messages':
            if flag.encode() not in backup_zip.read(info):
                return CheckResult.FLAG_NOT_FOUND, 'missing flag in backup'
        elif info.filename == 'public_key':
            pass
        elif info.filename == 'balance':
            pass
        else:
            return CheckResult.FLAG_NOT_FOUND, 'unexpected backup component'
    return CheckResult.OK, ''


class Checker(ServiceChecker):
    checks = RandomScheduler()

    def __init__(self, ip: str, team: int):
        super().__init__(self.checks, ip, team)
        self._users = None
        self._user_chat_src = None
        self._user_chat_dst = None
        self._chat_send_msg = None
        self._user_tx_src = None
        self._user_tx_dst = None
        self._mint_amount = None
        self._currency = None
        self._transfer_amount = None
        self._receipt = None
        self._user_backup_1 = None
        self._backup_1_id = None
        self._backup_2_ref = None
        self._user_backup_2 = None
        self._backup_2_id = None

    def _place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        with ExceptionContext('failed to create users', result=CheckResult.FLAG_NOT_FOUND):
            user_receiver = get_tick_randuser_auth(
                flag, 'receiver', self._client)
            user_sender = get_tick_randuser_auth(flag, 'sender', self._client)
        self._rand_reconnect()

        with ExceptionContext('failed to send message', result=CheckResult.FLAG_NOT_FOUND):
            self._client.chat_send(user_receiver.userid, flag)
        self._rand_reconnect()
        with ExceptionContext('failed to create backup', result=CheckResult.FLAG_NOT_FOUND):
            backup_id = self._client.new_backup()
        self._rand_reconnect()

        result, error = check_backup(self._client, backup_id, flag)
        if result != CheckResult.OK:
            return result, error

        checkerlib.set_flagid(f'backup:{user_sender.userid}/{backup_id}')

        return CheckResult.OK, ''

    def _check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)

        if not flagid:
            logging.info('No flagid saved for this team and tick')
            return CheckResult.FLAG_NOT_FOUND, 'flag was not placed successfully'

        _, backup_id = flagid[len('backup:'):].split('/')

        with ExceptionContext('authentication failed', result=CheckResult.FLAG_NOT_FOUND):
            get_tick_randuser_auth(flag, 'sender', self._client)
        self._rand_reconnect()

        result, error = check_backup(self._client, backup_id, flag)
        if result != CheckResult.OK:
            return result, error

        return CheckResult.OK, ''

    @checks.task('echo')
    @ExceptionContext('echo failed')
    def checks_echo(self) -> Tuple[CheckResult, str]:
        self._client.echo(randstr(32).encode())
        return CheckResult.OK, ''

    @checks.task('create_users')
    @ExceptionContext('failed to create users')
    def checks_create_users(self) -> Tuple[CheckResult, str]:
        self._users = []
        for _ in range(2):
            self._users.append(randuser_auth(self._client))
        return CheckResult.OK, ''

    @checks.task('userid', 'create_users')
    @ExceptionContext('get user ID failed')
    def checks_get_userid(self) -> Tuple[CheckResult, str]:
        user1, user2 = random.sample(self._users, 2)
        self._client.user = user1
        userid = self._client.get_userid(user2.username)
        if userid != user2.userid:
            return CheckResult.FAULTY, 'get user ID: wrong ID'
        return CheckResult.OK, ''

    @checks.task('username', 'create_users')
    @ExceptionContext('get username failed')
    def checks_get_username(self) -> Tuple[CheckResult, str]:
        user1, user2 = random.sample(self._users, 2)
        self._client.user = user1
        username = self._client.get_username(user2.userid)
        if username != user2.username:
            return CheckResult.FAULTY, 'get username: wrong username'
        return CheckResult.OK, ''

    @checks.task('pubkey', 'create_users')
    @ExceptionContext('get public key failed')
    def checks_get_pubkey(self) -> Tuple[CheckResult, str]:
        user1, user2 = random.sample(self._users, 2)
        self._client.user = user1
        pubkey = self._client.get_pubkey(user2.userid)
        if pubkey != user2.pubkey:
            return CheckResult.FAULTY, 'get public key: wrong key'
        return CheckResult.OK, ''

    @checks.task('chat_send', 'create_users')
    @ExceptionContext('chat send failed')
    def checks_chat_send(self) -> Tuple[CheckResult, str]:
        self._user_chat_src, self._user_chat_dst = random.sample(
            self._users, 2)
        self._client.user = self._user_chat_src
        self._chat_send_msg = random.choice(SET_PHRASES)
        self._client.chat_send(self._user_chat_dst.userid, self._chat_send_msg)
        return CheckResult.OK, ''

    @checks.task('chat_read', 'chat_send')
    @ExceptionContext('chat read failed')
    def checks_chat_read(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_chat_dst
        for _ in range(3):
            sender, _, content = self._client.chat_read()
            if content is None:
                continue
            if sender != self._user_chat_src.userid:
                return CheckResult.FAULTY, 'chat read: wrong sender'
            if content != self._chat_send_msg:
                return CheckResult.FAULTY, 'chat read: wrong content'
            return CheckResult.OK, ''
        return CheckResult.FAULTY, 'chat read: no message'

    @checks.task('pick_transfer_users', 'create_users')
    def checks_pick_transfer_users(self) -> Tuple[CheckResult, str]:
        self._user_tx_src, self._user_tx_dst = random.sample(self._users, 2)
        return CheckResult.OK, ''

    @checks.task('mint', 'pick_transfer_users')
    @ExceptionContext('mint failed')
    def checks_mint(self) -> Tuple[CheckResult, str]:
        self._mint_amount = random.randint(260000000, 2600000000)
        self._client.user = self._user_tx_src
        self._currency = self._client.mint(self._mint_amount)
        return CheckResult.OK, ''

    @checks.task('initial_balance_src', 'mint')
    @ExceptionContext('get initial balance (sender) failed')
    def checks_initial_balance_src(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_src
        if self._client.get_balance(self._currency) != self._mint_amount:
            return CheckResult.FAULTY, 'wrong balance after minting'
        return CheckResult.OK, ''

    @checks.task('initial_balance_dst', 'mint')
    @ExceptionContext('get initial balance (receiver) failed')
    def checks_initial_balance_dst(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_dst
        if self._client.get_balance(self._currency) != 10:
            return CheckResult.FAULTY, 'wrong initial balance'
        return CheckResult.OK, ''

    @checks.task('transfer', 'initial_balance_src')
    @ExceptionContext('transfer failed')
    def checks_transfer(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_src
        self._transfer_amount = random.randint(0, self._mint_amount)
        self._receipt = self._client.transfer(
            self._user_tx_dst.userid, self._currency, self._transfer_amount)
        if self._receipt.amount != self._transfer_amount:
            return CheckResult.FAULTY, 'wrong amount in receipt'
        if self._receipt.currency != self._currency:
            return CheckResult.FAULTY, 'wrong currency in receipt'
        if self._receipt.recipient_userid != self._user_tx_dst.userid:
            return CheckResult.FAULTY, 'wrong recipient in receipt'
        return CheckResult.OK, ''

    @checks.task('check_receipt', 'transfer')
    @ExceptionContext('check receipt failed')
    def checks_check_receipt(self) -> Tuple[CheckResult, str]:
        self._client.user = random.choice(self._users)
        self._client.check_receipt(self._receipt)
        return CheckResult.OK, ''

    @checks.task('receive', 'initial_balance_dst', 'check_receipt')
    @ExceptionContext('transfer failed')
    def checks_receive(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_dst
        self._client.receive(self._receipt)
        return CheckResult.OK, ''

    @checks.task('final_balance_src', 'transfer')
    @ExceptionContext('get final balance (sender) failed')
    def checks_final_balance_src(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_src
        if self._client.get_balance(self._currency) != self._mint_amount - self._transfer_amount:
            return CheckResult.FAULTY, 'wrong balance after transfer'
        return CheckResult.OK, ''

    @checks.task('final_balance_dst', 'receive')
    @ExceptionContext('get final balance (receiver) failed')
    def checks_final_balance_dst(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_tx_dst
        if self._client.get_balance(self._currency) != 10 + self._transfer_amount:
            return CheckResult.FAULTY, 'wrong balance after receive'
        return CheckResult.OK, ''

    @checks.task('new_backup_1', 'chat_send')
    @ExceptionContext('new backup failed')
    def checks_new_backup_1(self) -> Tuple[CheckResult, str]:
        self._user_backup_1 = random.choice(
            [self._user_chat_src, self._user_chat_dst])
        self._client.user = self._user_backup_1
        self._backup_1_id = self._client.new_backup()
        return CheckResult.OK, ''

    @checks.task('get_backup_1', 'new_backup_1')
    @ExceptionContext('get backup failed')
    def checks_get_backup_1(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_backup_1
        backup_content = self._client.get_backup(self._backup_1_id)
        if len(backup_content) > MAX_MESSAGE_LEN:
            return CheckResult.FAULTY, 'backup too big'
        bio = io.BytesIO(backup_content)
        with zipfile.ZipFile(bio) as zf:
            if zf.getinfo('messages').file_size > MAX_MESSAGE_LEN:
                return CheckResult.FAULTY, 'backup messages too big'
            if self._chat_send_msg.encode() not in zf.read('messages'):
                return CheckResult.FAULTY, 'wrong messages in backup'
        return CheckResult.OK, ''

    @checks.task('new_backup_2', 'create_users')
    @ExceptionContext('new backup failed')
    def checks_new_backup_2(self) -> Tuple[CheckResult, str]:
        self._user_backup_2 = random.choice(self._users)
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w', compresslevel=random.randint(0, 4)) as zf:
            zf.writestr('messages', randstr(random.randint(10, 800)))
            zf.writestr('public_key', self._user_backup_2.pubkey)
            zf.writestr('balance', randstr(random.randint(10, 800)))
        self._backup_2_ref = bio.getvalue()
        self._client.user = self._user_backup_2
        self._backup_2_id = self._client.new_backup(self._backup_2_ref)
        return CheckResult.OK, ''

    @checks.task('get_backup_2', 'new_backup_2')
    @ExceptionContext('get backup failed')
    def checks_get_backup_2(self) -> Tuple[CheckResult, str]:
        self._client.user = self._user_backup_2
        backup = self._client.get_backup(self._backup_2_id)
        if len(backup) > MAX_MESSAGE_LEN:
            return CheckResult.FAULTY, 'backup too big'
        bio_ref = io.BytesIO(self._backup_2_ref)
        bio_backup = io.BytesIO(backup)
        with zipfile.ZipFile(bio_ref) as zf_ref:
            names_ref = zf_ref.namelist()
            with zipfile.ZipFile(bio_backup) as zf_backup:
                names_backup = zf_backup.namelist()
                if set(names_ref) != set(names_backup):
                    return CheckResult.FAULTY, 'wrong filenames in backup'
                for name in names_ref:
                    info_ref = zf_ref.getinfo(name)
                    info_backup = zf_backup.getinfo(name)
                    if info_backup.file_size != info_ref.file_size:
                        return CheckResult.FAULTY, 'wrong file size in backup'
                    if zf_backup.read(name) != zf_ref.read(name):
                        return CheckResult.FAULTY, 'wrong file content in backup'
        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(Checker)
