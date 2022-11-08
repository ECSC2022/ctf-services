#!/usr/bin/env python3

import random
import string
import argparse

from benchlib import Worker, Benchmark
from bot_client import BotClient
from client import Client, User


BOT_USERNAME = 'marketbot'


def randstr(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=length))


class WorkerImpl(Worker):
    def __init__(self, host: str, port: int, username: str, password: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._host = host
        self._port = port
        self._username = username if username is not None else randstr(16)
        self._password = password if password is not None else randstr(16)
        self._client = None
        self._bot = None

    def initialize(self):
        self._client = Client()
        self._client.connect(self._host, self._port)
        self._client.user = User(self._username, self._password)
        self._client.register(exist_ok=True)
        self._client.auth()
        bot_uid = self._client.get_userid(BOT_USERNAME)
        self._bot = BotClient(self._client, bot_uid)

    def request(self) -> int:
        self._bot.chat('/help')
        return 1


def main():
    parser = argparse.ArgumentParser(description='Bot benchmark.')
    parser.add_argument('-H', '--host', default='127.0.0.1',
                        help='Server host.')
    parser.add_argument('-p', '--port', type=int,
                        default=10050, help='Server port.')
    parser.add_argument('-u', '--username', default=None, help='Username.')
    parser.add_argument('-P', '--password', default=None, help='Password.')
    Benchmark.add_args(parser)
    args = parser.parse_args()

    bench = Benchmark.from_args(
        args, WorkerImpl, args.host, args.port, args.username, args.password)

    bench.run()


if __name__ == '__main__':
    main()
