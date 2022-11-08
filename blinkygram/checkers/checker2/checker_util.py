#!/usr/bin/env python3

import random
import string
import logging
import functools

from typing import Callable, Tuple

from client import Client, User
from checker_rand import RandomChecker, RandomScheduler

from ctf_gameserver.checkerlib import CheckResult


# Random username length.
USERNAME_LENGTH = 16
# Random password length.
PASSWORD_LENGTH = 32

# Probability of reconnecting between random checks.
RECONNECT_PROB = 0.25

# Service port.
SERVICE_PORT = 10050


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
    client.register(exist_ok=True)
    client.auth()
    return user


class CheckerExit(Exception):
    def __init__(self, result: CheckResult, comment: str):
        super().__init__()
        self.result = result
        self.comment = comment


class ExceptionContext:
    def __init__(self, comment: str, result: CheckResult = CheckResult.FAULTY,
                 toplevel: bool = False):
        self._comment = comment
        self._result = result
        self._toplevel = toplevel

    def __call__(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # The FAUST checklib treats all timeouts as network errors (DOWN).
            # This is not always correct in our case (e.g., a reply smaller
            # than expected will trigger a timeout, but it's a protocol problem,
            # not a network one). Therefore, we manually handle exceptions as
            # FAULTY, and special-case when they mean DOWN (e.g., connect).
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if self._toplevel:
                    logging.exception(self._comment)
                    if isinstance(e, CheckerExit):
                        return e.result, e.comment
                    return self._result, self._comment
                else:
                    if isinstance(e, CheckerExit):
                        raise e
                    raise CheckerExit(self._result, self._comment) from e
        return wrapper

    def __enter__(self):
        assert not self._toplevel

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert not self._toplevel
        if exc_value is not None:
            raise CheckerExit(self._result, self._comment) from exc_value


class ServiceChecker(RandomChecker):
    def __init__(self, checks: RandomScheduler, ip: str, team: int):
        super().__init__(checks, ip, team)
        self._ip = ip
        self._port = SERVICE_PORT
        self._team = team
        self._client = Client()

    @ExceptionContext('error placing flag', toplevel=True)
    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        try:
            self._connect()
            return self._place_flag(tick)
        finally:
            self._disconnect()

    @ExceptionContext('error checking flag', result=CheckResult.FLAG_NOT_FOUND,
                      toplevel=True)
    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        try:
            self._connect()
            return self._check_flag(tick)
        finally:
            self._disconnect()

    @ExceptionContext('error checking service', toplevel=True)
    def check_service(self) -> Tuple[CheckResult, str]:
        # Avoid conflicts with deterministic seeding of place/check flag
        random.seed()
        try:
            return super().check_service()
        finally:
            self._disconnect()

    @ExceptionContext('error checking service', toplevel=True)
    def before_check(self) -> Tuple[CheckResult, str]:
        self._rand_reconnect()
        return CheckResult.OK, ''

    @ExceptionContext('cannot connect', result=CheckResult.DOWN)
    def _connect(self, reconnect=False):
        if self._client.connected:
            if not reconnect:
                return
            self._client.close()
        self._client.connect(self._ip, self._port)

    def _disconnect(self):
        if self._client.connected:
            self._client.close()

    def _rand_reconnect(self):
        if not self._client.connected or random.random() < RECONNECT_PROB:
            self._connect(reconnect=True)

    def _place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        return CheckResult.OK, ''

    def _check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        return CheckResult.OK, ''
