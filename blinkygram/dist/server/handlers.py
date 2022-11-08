import asyncio
import dataclasses
import os
import json
import shutil
import shlex
import sys
import tempfile
import traceback
import uuid

from collections import OrderedDict
from hashlib import sha256

from globals import G
from utils import USER_BACKUP

from auth import *
from database import *
from protocol import *


MAX_CHAT_MSG_LEN = 1000

INITIAL_BALANCE = 10

MAX_USER_BACKUPS = 5
MAX_USER_BACKUP_SIZE = 1 << 12

LOG_REQUESTS = False


class HandlerException(Exception):
    pass


class MessageCache:
    _lock = asyncio.Lock()
    _uid_conds = OrderedDict()

    _CACHE_SIZE = 1000

    @staticmethod
    async def read_one(uid: int, timeout: float = 5.0) -> Optional[Message]:
        async with MessageCache._lock:
            msg = await Message.read_one(G.db, uid)
            if msg is not None:
                return msg
            cond = MessageCache._get_uid_cond(uid, add=True)
            try:
                await asyncio.wait_for(cond.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
            return await Message.read_one(G.db, uid)

    @staticmethod
    async def notify_one(uid: int):
        async with MessageCache._lock:
            cond = MessageCache._get_uid_cond(uid)
            if cond is not None:
                cond.notify()

    @staticmethod
    def _get_uid_cond(uid: int, add: bool = False) -> Optional[asyncio.Condition]:
        if uid in MessageCache._uid_conds:
            MessageCache._uid_conds.move_to_end(uid)
        elif add:
            while len(MessageCache._uid_conds) >= MessageCache._CACHE_SIZE:
                MessageCache._uid_conds.popitem(last=False)
            MessageCache._uid_conds[uid] = asyncio.Condition(
                MessageCache._lock)
        return MessageCache._uid_conds.get(uid)


handler_map = {}


def handler(req_cls: type):
    def decorator(func):
        handler_map[req_cls] = func
        return func
    return decorator


def authenticated(func):
    async def wrapper(req):
        if not G.auth.check_token(req.auth_token):
            return ReplyMessage.fail('Unauthorized')
        return await func(req, req.auth_token.userid)
    return wrapper


async def handle_request(req: RequestMessage):
    if LOG_REQUESTS:
        print(f'Request: {req}', file=sys.stderr)
    try:
        func = handler_map[req.__class__]
    except KeyError:
        raise HandlerException('No handler found')
    return await func(req)


async def get_balance(userid: int, currency: int) -> Balance:
    balance = await Balance.find(G.db, userid, currency)
    if balance is None:
        balance = Balance(userid, currency, INITIAL_BALANCE)
        await balance.commit(G.db)
    return balance


@handler(EchoRequest)
async def echo_handler(req: EchoRequest):
    return ReplyMessage.ok(EchoReply(req.data))


@handler(RegisterRequest)
async def register_handler(req: RegisterRequest):
    if deserialize_pubkey(req.pubkey) is None:
        return ReplyMessage.fail('Invalid public key')
    try:
        password = sha256(req.password.encode()).hexdigest()
        user = User(req.username, password, req.pubkey)
        await user.commit(G.db)
        return ReplyMessage.ok()
    except UserExists:
        return ReplyMessage.fail('User exists')


@handler(AuthRequest)
async def auth_handler(req: AuthRequest):
    user = await User.by_name(G.db, req.username)
    if user is None:
        return ReplyMessage.fail('User not found')
    if sha256(req.password.encode()).hexdigest() != user.password:
        return ReplyMessage.fail('Wrong password')
    token = G.auth.make_token(user.id)
    return ReplyMessage.ok(AuthReply(token))


@handler(UseridRequest)
@authenticated
async def userid_handler(req: UseridRequest, userid: int):
    user = await User.by_name(G.db, req.username)
    if user is None:
        return ReplyMessage.fail('User not found')
    return ReplyMessage.ok(UseridReply(user.id))


@handler(UsernameRequest)
@authenticated
async def username_handler(req: UsernameRequest, userid: int):
    user = await User.by_id(G.db, req.userid)
    if user is None:
        return ReplyMessage.fail('User not found')
    return ReplyMessage.ok(UsernameReply(user.username))


@handler(PubkeyRequest)
@authenticated
async def pubkey_handler(req: PubkeyRequest, userid: int):
    user = await User.by_id(G.db, req.userid)
    if user is None:
        return ReplyMessage.fail('User not found')
    return ReplyMessage.ok(PubkeyReply(user.pubkey))


@handler(ChatSendRequest)
@authenticated
async def chat_send_handler(req: ChatSendRequest, userid: int):
    if len(req.content) > MAX_CHAT_MSG_LEN:
        return ReplyMessage.fail('Message too long')
    recipient = await User.by_id(G.db, req.recipient_userid)
    if recipient is None:
        return ReplyMessage.fail('Recipient not found')
    msg = Message(userid, req.recipient_userid, req.content)
    await msg.commit(G.db)
    await MessageCache.notify_one(req.recipient_userid)
    return ReplyMessage.ok()


@handler(ChatReadRequest)
@authenticated
async def chat_read_handler(req: ChatReadRequest, userid: int):
    msg = await MessageCache.read_one(userid)
    if msg is None:
        return ReplyMessage.fail('No messages')
    return ReplyMessage.ok(ChatReadReply(msg.uid_src, msg.timestamp, msg.content))


@handler(BalanceRequest)
@authenticated
async def balance_handler(req: BalanceRequest, userid: int):
    try:
        balance = await get_balance(userid, req.currency)
    except CurrencyNotExists:
        return ReplyMessage.fail('Unknown currency')
    return ReplyMessage.ok(BalanceReply(balance.balance))


@handler(TransferRequest)
@authenticated
async def transfer_handler(req: TransferRequest, userid: int):
    try:
        await get_balance(userid, req.currency)
    except CurrencyNotExists:
        return ReplyMessage.fail('Unknown currency')
    if not await Balance.adjust(G.db, userid, req.currency, -req.amount):
        return ReplyMessage.fail('Insufficient balance')
    receipt = G.auth.make_receipt(
        req.amount, req.currency, req.recipient_userid)
    return ReplyMessage.ok(TransferReply(receipt))


@handler(ReceiveRequest)
@authenticated
async def receive_handler(req: ReceiveRequest, userid: int):
    if not G.auth.check_receipt(req.receipt):
        return ReplyMessage.fail('Invalid receipt')
    if userid != req.receipt.recipient_userid:
        return ReplyMessage.fail('Not your receipt')
    if not await SpentReceipt.spend(G.db, req.receipt.dt_encode()):
        return ReplyMessage.fail('Already spent')
    try:
        await get_balance(userid, req.receipt.currency)
    except CurrencyNotExists:
        return ReplyMessage.fail('Unknown currency')
    await Balance.adjust(G.db, userid, req.receipt.currency, req.receipt.amount)
    return ReplyMessage.ok()


@handler(CheckReceiptRequest)
@authenticated
async def check_receipt_handler(req: CheckReceiptRequest, userid: int):
    if not G.auth.check_receipt(req.receipt):
        return ReplyMessage.fail('Invalid receipt')
    if await SpentReceipt.find(G.db, req.receipt.dt_encode()):
        return ReplyMessage.fail('Already spent')
    return ReplyMessage.ok()


@handler(MintRequest)
@authenticated
async def mint_handler(req: MintRequest, userid: int):
    currency = Currency()
    await currency.commit(G.db)
    balance = Balance(userid, currency.id, req.amount)
    await balance.commit(G.db)
    return ReplyMessage.ok(MintReply(currency.id))


@handler(NewBackupRequest)
@authenticated
async def new_backup_handler(req: NewBackupRequest, userid: int):
    backup_id = str(uuid.uuid4())
    user_backups_dir = f'{G.backup_path}/{userid}'
    backup_dir = f'{user_backups_dir}/{backup_id}'

    try:
        os.makedirs(backup_dir)
        os.chmod(user_backups_dir, 0o777)
        os.chmod(backup_dir, 0o777)

        existing_backups = [f'{user_backups_dir}/{name}'
                            for name in os.listdir(user_backups_dir)]
        if len(existing_backups) >= MAX_USER_BACKUPS-1:
            existing_backups.sort(key=os.path.getctime)
            for path in existing_backups[:-(MAX_USER_BACKUPS-1)]:
                shutil.rmtree(path, ignore_errors=True)

        if len(req.data) > 0 and len(req.data) < MAX_USER_BACKUP_SIZE:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpzip = f'{tmpdir}/backup.zip'
                with open(tmpzip, 'wb') as f:
                    f.write(req.data)
                os.chmod(tmpdir, 0o777)
                os.chmod(tmpzip, 0o664)
                process = await asyncio.subprocess.create_subprocess_exec(
                    'sudo', '-u', USER_BACKUP, '--', 'sh', '-c',
                    f'ulimit -f 64 && cd {backup_dir} && unzip {tmpzip} messages public_key balance',
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
                if process.returncode != 0:
                    return ReplyMessage.fail(f'Backup failed (cannot unzip)')
        else:
            with open(f'{backup_dir}/messages', 'w') as f:
                msgs = await Message.all_by_user(G.db, userid)
                json.dump([dataclasses.asdict(msg) for msg in msgs], f)
            os.chmod(f'{backup_dir}/messages', 0o664)
            with open(f'{backup_dir}/public_key', 'w') as f:
                user = await User.by_id(G.db, userid)
                f.write(user.pubkey)
            os.chmod(f'{backup_dir}/public_key', 0o664)
            with open(f'{backup_dir}/balance', 'w') as f:
                balances = await Balance.all_by_user(G.db, userid)
                json.dump([dataclasses.asdict(balance)
                           for balance in balances], f)
            os.chmod(f'{backup_dir}/balance', 0o664)
    except Exception:
        traceback.print_exc()
        return ReplyMessage.fail(f'Backup failed')

    return ReplyMessage.ok(NewBackupReply(backup_id))


@handler(GetBackupRequest)
@authenticated
async def get_backup_handler(req: GetBackupRequest, userid: int):
    user_backups_dir = f'{G.backup_path}/{userid}'
    backup_dir = f'{user_backups_dir}/{req.id}'

    if not os.path.isdir(backup_dir):
        return ReplyMessage.fail(f'Backup not found')

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpzip = f'{tmpdir}/backup.zip'
            os.chmod(tmpdir, 0o777)
            process = await asyncio.subprocess.create_subprocess_exec(
                'sudo', '-u', USER_BACKUP, '--', 'sh', '-c',
                f'ulimit -f 64 && cd {shlex.quote(backup_dir)} && zip {tmpzip} messages public_key balance && chmod 664 {tmpzip}',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            if process.returncode != 0:
                return ReplyMessage.fail(f'Get backup failed (cannot zip)')
            with open(tmpzip, 'rb') as f:
                backup = f.read()
    except Exception:
        traceback.print_exc()
        return ReplyMessage.fail(f'Get backup failed')

    return ReplyMessage.ok(GetBackupReply(backup))
