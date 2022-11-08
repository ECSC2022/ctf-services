#!/usr/bin/env python3

import os
import random
import signal
import sys
import time
import asyncio
import multiprocessing

from typing import Awaitable

from auth import Authenticator
from database import Database
from globals import G
from protocol import MessageHeader, RequestMessage
from handlers import handle_request
from utils import set_perms_server


BIND_HOST = os.environ['SERVER_BIND_HOST']
BIND_PORT = int(os.environ['SERVER_BIND_PORT'])
WORKERS = int(os.environ['SERVER_WORKERS'])
THROTTLE_RPS = float(os.environ['SERVER_THROTTLE_RPS'])

SOCKET_TIMEOUT = 30

STORAGE_PATH = './storage'
BACKUP_PATH = f'{STORAGE_PATH}/backups'
DB_PATH = f'{STORAGE_PATH}/data.db'
SK_PATH = f'{STORAGE_PATH}/sk.pem'


async def timeout(aw: Awaitable) -> Awaitable:
    return await asyncio.wait_for(aw, timeout=SOCKET_TIMEOUT)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        try:
            hdr_bs = await timeout(reader.readexactly(MessageHeader.SIZE))
        except asyncio.IncompleteReadError as e:
            if len(e.partial) == 0:
                break
            raise e

        hdr = MessageHeader.dt_decode(hdr_bs)
        msg_bs = await timeout(reader.readexactly(hdr.length))
        msg = RequestMessage.dt_decode(msg_bs)

        t1 = time.time()
        reply = await handle_request(msg.req)
        reply_bs = reply.dt_encode()
        reply_hdr_bs = MessageHeader(hdr.seq, len(reply_bs)).dt_encode()
        writer.write(reply_hdr_bs + reply_bs)
        await timeout(writer.drain())
        t2 = time.time()

        throttle_sleep = 1 / THROTTLE_RPS - (t2 - t1)
        if throttle_sleep > 0:
            await asyncio.sleep(throttle_sleep)


async def initialize_worker():
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, loop.stop)

    G.backup_path = BACKUP_PATH
    G.auth = Authenticator.from_path(SK_PATH)
    G.db = Database(DB_PATH, concurrency=WORKERS)
    await G.db.connect()


async def shutdown_worker():
    await G.db.close()


async def worker_main():
    await initialize_worker()
    server = await asyncio.start_server(
        handle_client, BIND_HOST, BIND_PORT, reuse_port=True)
    async with server:
        await server.serve_forever()


def worker():
    print(f'Worker running')
    sys.stdout.flush()

    random.seed()

    try:
        asyncio.run(worker_main())
    finally:
        asyncio.run(shutdown_worker())


async def initialize_main():
    os.makedirs(STORAGE_PATH, exist_ok=True)
    os.makedirs(BACKUP_PATH, exist_ok=True)
    os.chmod(BACKUP_PATH, 0o777)

    Authenticator.from_path(SK_PATH)
    set_perms_server(SK_PATH)

    db = Database(DB_PATH)
    await db.connect()
    await db.close()
    set_perms_server(DB_PATH)


def main():
    print(f'Starting up on {BIND_HOST}:{BIND_PORT} with {WORKERS} workers')
    sys.stdout.flush()

    asyncio.run(initialize_main())

    procs = [multiprocessing.Process(target=worker) for _ in range(WORKERS)]
    for proc in procs:
        proc.start()

    def sigterm_handler(signum, frame):
        for proc in procs:
            proc.terminate()
    signal.signal(signal.SIGTERM, sigterm_handler)

    for proc in procs:
        proc.join()


if __name__ == '__main__':
    main()
