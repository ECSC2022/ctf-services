#!/usr/bin/env python3
import enum
import logging
import random
import re
import string
import subprocess
from typing import Tuple

from pwn import *
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

NUM_MODELS = 5

model_details = {
    1: {"Name": "SUPER POWERPLANT 1","Swep Area":11.7},
    2: {"Name": "SUPER POWERPLANT 2","Swep Area":50},
    3: {"Name": "SUPER POWERPLANT 3","Swep Area":100},
    4: {"Name": "SUPER POWERPLANT 4","Swep Area":150},
    5: {"Name": "SUPER POWERPLANT 5","Swep Area":170},
}

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


def register_random_user(r):
    username = randoms(128, string.ascii_lowercase + string.digits + "-")
    password = randoms(128, string.ascii_lowercase + string.digits + "-")

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
    return username,password

def login_user(r,username:str,password:str):
    r.sendline(Menu.LOGIN.value)
    response = r.recvuntil(b"Username: ")
    if b"Username: " != response:
        return CheckResult.FAULTY, "Service did not ask for username"
    r.sendline(username.encode())
    response = r.recvuntil(b"Password: ")
    if b"Password: " != response:
        return CheckResult.FAULTY, "Service did not ask for password"
    r.sendline(password.encode())
    response = r.recvuntil(Menu.MENU_END.value)
    if not response.startswith(b"Logged in successfully"):
        return CheckResult.FAULTY, "Could not login"
    return True, True

def register_turbine(r):
    r.sendline(Menu.REGISTER_TURBINE.value)
    response = r.recvline()
    m = re.match(b"UUID is: ([a-z0-9-]+)\r\n", response)
    if not m:
        return CheckResult.FAULTY, "Could not parse turbine ID"
    turbine_id = m.group(1).decode()

    response = r.recvuntil(b"Description: ")
    if b"Description: " != response:
        return CheckResult.FAULTY, "Service did not ask for description"
    
    description = randoms(42, string.ascii_lowercase + string.digits + "-")
    r.sendline(description.encode())

    model = random.randint(1, NUM_MODELS)
    response = r.recvuntil(b"Model number: ")
    if b"Model number: " != response:
        return CheckResult.FAULTY, "Service did not ask for model number"
    r.sendline(str(model).encode())

    checksum = subprocess.check_output(["/checker/checksum", turbine_id, str(model)])
    response = r.recvuntil(b"Checksum: ")
    if response != b"Checksum: ":
        return CheckResult.FAULTY, "Service did not ask for checksum"
    r.sendline(checksum)

    response = r.recvuntil(Menu.MENU_END.value)
    if not response.startswith(b"Turbine registered successfully"):
        return CheckResult.FAULTY, "Could not register turbine"
    return turbine_id,checksum

def show_turbine_details(r,turbine_id:str,checksum:str):
    r.sendline(Menu.SHOW_TURBINE_DETAILS.value)
    response = r.recvuntil(b"Enter the ID of the turbine to display: ")
    if not response.startswith(b"Enter the ID of the turbine to display: "):
        return CheckResult.FAULTY, "Service did not ask for turbine ID"
    r.sendline(turbine_id.encode())

    response = r.recvuntil(b"Enter the checksum of the turbine to display: ")
    if not response.startswith(b"Enter the checksum of the turbine to display: "):
        return CheckResult.FAULTY, "Service did not ask for turbine checksum"
    r.sendline(checksum)

    response = r.recvuntil(Menu.MENU_END.value)
    m = re.search(b"Description: (.+)\r\n", response)
    if not m:
        return CheckResult.FAULTY, "Turbine description not displayed"

    m = re.search(b"Model number: (.+)\r\n", response)
    if not m:
        return CheckResult.FAULTY, "Turbine model number not displayed"
    elif int(m.group(1)) not in model_details:
        return CheckResult.FAULTY, "Turbine model number is invalid"

    m = re.search(b"Name: (.+)\r\n", response)
    if not m:
        return CheckResult.FAULTY, "Turbine name not displayed"
    
    m = re.search(b"Swep area: (.+)\r\n", response)
    if not m:
        return CheckResult.FAULTY, "Swep area not found"

def calculate_capacity(r,turbine_id_list:list,checksum_list:list):
    num_turbines = len(turbine_id_list)
    print(f"Num_turbines: {num_turbines}")
    average_wind_velocity = random.random() * 10000 % 100

    r.sendline(Menu.CALCULATE_CAPACITY.value)
    response = r.recvuntil(b"Average Wind Velocity:")
    
    if not response.startswith(b"Average Wind Velocity:"):
        return CheckResult.FAULTY, "Service did not ask for wind velocity"
    r.sendline(str(average_wind_velocity).encode())

    response = r.recvuntil(b"Enter the number of the turbines to calculate:")
    if not response.startswith(b"Enter the number of the turbines to calculate:"):
        return CheckResult.FAULTY, "Service did not ask for turbine number"
    r.sendline(str(num_turbines).encode())

    response = r.recvuntil(b"Enter the IDs of the turbines to calculate:")
    print(response)
    if not response.startswith(b"Enter the IDs of the turbines to calculate:"):
        return CheckResult.FAULTY, "Service did not ask for turbine ids"

    for i in range(0,num_turbines):
        expected_num = str(i+1) + ":"
        response = r.recvuntil(expected_num.encode())
        turbine_id = turbine_id_list[i]
        if response != expected_num.encode():
            return CheckResult.FAULTY, "Service did not ask for the turbine id"
        r.sendline(turbine_id.encode())

    response = r.recvuntil(b" Enter the checksums of the turbines to calculate:")
    if not response.startswith(b"Enter the checksums of the turbines to calculate:"):
        return CheckResult.FAULTY, "Service did not ask for checksums"
    
    for i in range(0,num_turbines):
        response = r.recvuntil(expected_num.encode())
        checksum = checksum_list[i]
        r.sendline(checksum)
    
    response = r.recvuntil(b" Enter consumption array per household:")
    if not response.startswith(b" Enter consumption array per household:"):
        return CheckResult.FAULTY, "Service did not ask for consumption array"

    for i in range(0,3):
       vals = "{} {} {}".format(random.random()*10000%100,
       random.random()*10000%100,random.random()*10000%100)
       r.sendline(vals.encode())
    
    response = r.recvuntil(b"Enter the initial guess vector:")
    if not response.startswith(b" Enter the initial guess vector:"):
        return CheckResult.FAULTY, "Service did not ask for guess vector"
    
    for i in range(0,3):
       vals = "{}".format(random.random()*10000%100)
       r.sendline(vals.encode())

    response = r.recvuntil("Stopped after:")
    logging.info(response)


class WindsOfThePastChecker2(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10060
        self.timeout = 5
        context.timeout = 5

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        with remote(self.ip, self.port) as r:
            response = r.recvuntil(Menu.MENU_END.value)
            if not response:
                return CheckResult.FAULTY, "Could not load initial menu"

            username = randoms(128, string.ascii_lowercase + string.digits + "-")
            password = randoms(128, string.ascii_lowercase + string.digits + "-")

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

            r.sendline(Menu.LOGIN.value)
            response = r.recvuntil(b"Username: ")
            if b"Username: " != response:
                return CheckResult.FAULTY, "Service did not ask for username"
            r.sendline(username.encode())
            response = r.recvuntil(b"Password: ")
            if b"Password: " != response:
                return CheckResult.FAULTY, "Service did not ask for password"
            r.sendline(password.encode())
            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(b"Logged in successfully"):
                return CheckResult.FAULTY, "Could not login"

            r.sendline(Menu.REGISTER_TURBINE.value)
            response = r.recvline()
            m = re.match(b"UUID is: ([a-z0-9-]+)\r\n", response)
            if not m:
                return CheckResult.FAULTY, "Could not parse turbine ID"
            turbine_id = m.group(1).decode()

            response = r.recvuntil(b"Description: ")
            if b"Description: " != response:
                return CheckResult.FAULTY, "Service did not ask for description"
            r.sendline(flag.encode())

            model = random.randint(1, NUM_MODELS)
            response = r.recvuntil(b"Model number: ")
            if b"Model number: " != response:
                return CheckResult.FAULTY, "Service did not ask for model number"
            r.sendline(str(model).encode())

            checksum = subprocess.check_output(["/checker/checksum", turbine_id, str(model)]).strip()
            response = r.recvuntil(b"Checksum: ")
            if response != b"Checksum: ":
                return CheckResult.FAULTY, "Service did not ask for checksum"
            r.sendline(checksum)

            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(b"Turbine registered successfully"):
                return CheckResult.FAULTY, "Could not register turbine"

            r.sendline(Menu.EXIT.value)

            checkerlib.set_flagid(turbine_id)
            checkerlib.store_state(turbine_id, {
                "checksum": checksum,
                "username": username,
                "password": password,
            })
            return CheckResult.OK, ""

    def check_service(self) -> Tuple[CheckResult, str]:
        try:
            with remote(self.ip, self.port):
                pass
        except:
            return CheckResult.DOWN, "Could not connect to service"
        return CheckResult.OK, ""

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        expected_flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)
        state = checkerlib.load_state(flagid)

        if not flagid:
            logging.info("No flagid saved for this team and tick")
            return CheckResult.FLAG_NOT_FOUND, "Flag was not placed successfully"

        with remote(self.ip, self.port) as r:
            if isinstance(state, bytes):
                username = randoms(128, string.ascii_lowercase + string.digits + "-")
                password = randoms(128, string.ascii_lowercase + string.digits + "-")
            else:
                username = state["username"]
                password = state["password"]


            response = r.recvuntil(Menu.MENU_END.value)
            if not response:
                return CheckResult.FAULTY, "Could not load initial menu"

            if isinstance(state, bytes):
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

            r.sendline(Menu.LOGIN.value)
            response = r.recvuntil(b"Username: ")
            if b"Username: " != response:
                return CheckResult.FAULTY, "Service did not ask for username"
            r.sendline(username.encode())
            response = r.recvuntil(b"Password: ")
            if b"Password: " != response:
                return CheckResult.FAULTY, "Service did not ask for password"
            r.sendline(password.encode())
            response = r.recvuntil(Menu.MENU_END.value)
            if not response.startswith(b"Logged in successfully"):
                return CheckResult.FAULTY, "Could not login"

            r.sendline(Menu.SHOW_TURBINE_DETAILS.value)
            response = r.recvuntil(b"Enter the ID of the turbine to display: ")
            if not response.startswith(b"Enter the ID of the turbine to display: "):
                return CheckResult.FAULTY, "Service did not ask for turbine ID"
            r.sendline(flagid.encode())

            response = r.recvuntil(b"Enter the checksum of the turbine to display: ")
            if not response.startswith(b"Enter the checksum of the turbine to display: "):
                return CheckResult.FAULTY, "Service did not ask for turbine checksum"
            if isinstance(state, bytes):
                checksum = state
            else:
                checksum = state["checksum"]
            r.sendline(checksum)

            response = r.recvuntil(Menu.MENU_END.value)
            m = re.search(b"Description: (.+)\r\n", response)
            if not m:
                return CheckResult.FLAG_NOT_FOUND, "Turbine description not displayed"
            found_flag = m.group(1).decode()

            m = re.search(b"Model number: (.+)\r\n", response)
            if not m:
                return CheckResult.FAULTY, "Turbine model number not displayed"
            elif int(m.group(1)) not in model_details:
                return CheckResult.FAULTY, "Turbine model number is invalid"
            
            m = re.search(b"Name: (.+)\r\n", response)
            if not m:
                return CheckResult.FAULTY, "Turbine name not displayed"
            
            m = re.search(b"Swep area: (.+)\r\n", response)
            if not m:
                return CheckResult.FAULTY, "Swep area not found"
            
            if found_flag != expected_flag:
                return CheckResult.FLAG_NOT_FOUND, "Invalid flag found"
            
            res, reason = register_random_user(r)
            if(res == CheckResult.FAULTY):
                return res, reason 
            username = res
            password = reason

            res, reason = login_user(r,username,password)
            if(res == CheckResult.FAULTY):
                return res, reason
            
            # create random number of turbines
            turbines = []
            checksums = []
            num_turbines = random.randint(1,7)
            for i in range(0,num_turbines):
                # turbine, checksum
                res, reason = register_turbine(r)
                if(res == CheckResult.FAULTY):
                    return res, reason
                turbines.append(res)
                checksums.append(reason)
            logging.info(checksums)
            logging.info(turbines)

            show_turbine_details(r,turbines[0],checksums[0])
            calculate_capacity(r,turbines,checksums)
            
            r.sendline(Menu.EXIT.value)



            return CheckResult.OK, ""


if __name__ == "__main__":
    checkerlib.run_check(WindsOfThePastChecker2)
