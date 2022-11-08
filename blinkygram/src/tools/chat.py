#!/usr/bin/env python3

import os
import sys
import time
import multiprocessing

from client import User, Client


def task_receive(host, port, username, password):
    client = Client(user=User(username, password))
    client.connect(host, port)

    client.register(exist_ok=True)
    client.auth()

    while True:
        _, _, msg = client.chat_read()
        if msg is not None:
            print(msg)
            sys.stdout.flush()


def task_send(host, port, username, password, recipient):
    sys.stdin = os.fdopen(0)

    client = Client(user=User(username, password))
    client.connect(host, port)

    client.register(exist_ok=True)
    client.auth()

    recipient_uid = client.get_userid(recipient)

    for line in sys.stdin:
        msg = line[:-1]
        client.chat_send(recipient_uid, msg)


def main():
    if len(sys.argv) != 6:
        print(f'Usage: {sys.argv[0]} <host> <port> <user> <password> <user to chat>',
              file=sys.stderr)
        exit(1)

    host, port, username, password, recipient = sys.argv[1:]
    port = int(port)

    proc_receive = multiprocessing.Process(
        target=lambda: task_receive(host, port, username, password))
    proc_receive.start()

    proc_send = multiprocessing.Process(
        target=lambda: task_send(host, port, username, password, recipient))
    proc_send.start()

    proc_send.join()
    proc_receive.terminate()


if __name__ == '__main__':
    main()
