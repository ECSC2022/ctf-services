#!/usr/bin/env python3
import enum
import logging
import string
from typing import Tuple

from pwn import *
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


class Menu(enum.Enum):
    EXIT = b"0"
    REGISTER_USER = b"1"
    LOGIN = b"2"
    SHOW_USER_DETAILS = b"3"
    SHOW_TURBINE_DETAILS = b"4"
    REGISTER_TURBINE = b"5"
    CALCULATE_CAPACITY = b"6"

    MENU_START = b"0. Exit"
    MENU_END = b"Select an option: "


class WindsOfThePastChecker1(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10060
        context.timeout = 5

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        with remote(self.ip, self.port) as r:
            response = r.recvuntil(Menu.MENU_END.value)
            if not response:
                return CheckResult.FAULTY, "Could not load initial menu"

            username = randoms(100, string.ascii_lowercase + string.digits + "-")
            password = flag

            r.sendline(Menu.REGISTER_USER.value)
            response = r.recvuntil(b"Username: ")
            if b"Username: " != response:
                return CheckResult.FAULTY, "Service did not ask for username"
            r.sendline(username.encode())
            response = r.recvuntil(b"Password: ")
            if b"Password: " != response:
                return CheckResult.FAULTY, "Service did not ask for password"
            r.sendline(password.encode())
            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(b"User registered"):
                return CheckResult.FAULTY, "Could not register user"

            r.sendline(Menu.EXIT.value)

            checkerlib.set_flagid(username)
            return CheckResult.OK, ""

    def check_service(self) -> Tuple[CheckResult, str]:
        try:
            with remote(self.ip, self.port):
                pass
        except:
            return CheckResult.DOWN, "Could not connect to service"
        return CheckResult.OK, ""

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)

        if not flagid:
            logging.info("No flagid saved for this team and tick")
            return CheckResult.FLAG_NOT_FOUND, "Flag was not placed successfully"

        with remote(self.ip, self.port) as r:
            response = r.recvuntil(Menu.MENU_END.value)
            if not response:
                return CheckResult.FAULTY, "Could not load initial menu"

            r.sendline(Menu.LOGIN.value)
            response = r.recvuntil(b"Username: ")
            if b"Username: " != response:
                return CheckResult.FAULTY, "Service did not ask for username"
            r.sendline(flagid.encode())
            response = r.recvuntil(b"Password: ")
            if b"Password: " != response:
                return CheckResult.FAULTY, "Service did not ask for password"
            r.sendline(flag.encode())
            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(b"Logged in successfully"):
                return CheckResult.FAULTY, "Could not login"

            r.sendline(Menu.SHOW_USER_DETAILS.value)
            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(f"User: {flagid} / {flag}\r\n".encode()):
                return CheckResult.FLAG_NOT_FOUND, "Could not show credentials"

            r.sendline(Menu.EXIT.value)

            return CheckResult.OK, ""


if __name__ == "__main__":
    checkerlib.run_check(WindsOfThePastChecker1)
