#!/usr/bin/env python3
import enum
import logging
import random
import re
import string
import subprocess
from typing import Tuple

from pwn import *
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
        print("Service did not ask for username")
    r.sendline(username.encode())
    response = r.recvuntil(b"Password: ")
    if b"Password: " != response:
        print("Service did not ask for password")
    r.sendline(password.encode())
    response = r.recvuntil(Menu.MENU_END.value)
    if not response.startswith(b"User registered"):
        print("Could not register user")
    
    return username,password

def login_user(r,username:str,password:str):
    r.sendline(Menu.LOGIN.value)
    response = r.recvuntil(b"Username: ")
    if b"Username: " != response:
        print("Service did not ask for username")
    r.sendline(username.encode())
    response = r.recvuntil(b"Password: ")
    if b"Password: " != response:
        print("Service did not ask for password")
    r.sendline(password.encode())
    response = r.recvuntil(Menu.MENU_END.value)
    if not response.startswith(b"Logged in successfully"):
        print("Could not login")
    return True, True

def register_turbine(r):
    r.sendline(Menu.REGISTER_TURBINE.value)
    response = r.recvline()
    m = re.match(b"UUID is: ([a-z0-9-]+)\r\n", response)
    if not m:
        print("Could not parse turbine ID")
    turbine_id = m.group(1).decode()

    response = r.recvuntil(b"Description: ")
    if b"Description: " != response:
        print("Service did not ask for description")
    
    description = randoms(42, string.ascii_lowercase + string.digits + "-")
    r.sendline(description.encode())

    model = random.randint(1, NUM_MODELS)
    response = r.recvuntil(b"Model number: ")
    if b"Model number: " != response:
        print("Service did not ask for model number")
    r.sendline(str(model).encode())

    checksum = subprocess.check_output(["./checksum", turbine_id, str(model)]).strip()
    response = r.recvuntil(b"Checksum: ")
    if response != b"Checksum: ":
        print("Service did not ask for checksum")
    r.sendline(checksum)

    response = r.recvuntil(Menu.MENU_END.value)
    if not response.startswith(b"Turbine registered successfully"):
        print("Could not register turbine")
    return turbine_id,checksum

def show_turbine_details(r,turbine_id:str,checksum:str):
    r.sendline(Menu.SHOW_TURBINE_DETAILS.value)
    response = r.recvuntil(b"Enter the ID of the turbine to display: ")
    if not response.startswith(b"Enter the ID of the turbine to display: "):
        print("Service did not ask for turbine ID")
    r.sendline(turbine_id.encode())

    response = r.recvuntil(b"Enter the checksum of the turbine to display: ")
    if not response.startswith(b"Enter the checksum of the turbine to display: "):
        print("Service did not ask for turbine checsum")
    r.sendline(checksum)

    response = r.recvuntil(Menu.MENU_END.value)
    m = re.search(b"Description: (.+)\r\n", response)
    if not m:
        print("Turbine description not displayed")

    m = re.search(b"Model number: (.+)\r\n", response)
    if not m:
        print("Turbine model number not displayed")
    elif int(m.group(1)) not in model_details:
        print("Turbine model number is invalid")

    m = re.search(b"Name: (.+)\r\n", response)
    if not m:
        print("Turbine name not displayed")
    
    m = re.search(b"Swep area: (.+)\r\n", response)
    if not m:
        print("Swep area not found")
    
def calculate_capacity(r,turbine_id_list:list,checksum_list:list):
    num_turbines = len(turbine_id_list)
    average_wind_velocity = random.random() * 10000 % 100

    r.sendline(Menu.CALCULATE_CAPACITY.value)
    response = r.recvuntil(b"Average Wind Velocity:")
    
    if not response.startswith(b"Average Wind Velocity:"):
        print("Service did not ask for wind velocity")
    r.sendline(str(average_wind_velocity).encode())

    response = r.recvuntil(b" Enter the number of the turbines to calculate:")
    if not response.startswith(b" Enter the number of the turbines to calculate:"):
        print("Service did not ask for turbine number")
    r.sendline(str(num_turbines).encode())

    response = r.recvuntil(b" Enter the IDs of the turbines to calculate:")
    if not response.startswith(b" Enter the IDs of the turbines to calculate:"):
        print("Service did not ask for turbine ids")
    for i in range(0,num_turbines):
        expected_num = str(i+1) + ":"
        response = r.recvuntil(expected_num.encode())
        turbine_id = turbine_id_list[i].strip()
        r.sendline(turbine_id.encode())

    response = r.recvuntil(b" Enter the checksums of the turbines to calculate:")
    if not response.startswith(b" Enter the checksums of the turbines to calculate:"):
        print("Service did not ask for checksums")
    
    for i in range(0,num_turbines):
        expected_num = str(i+1) + ":"
        response = r.recvuntil(expected_num.encode())
        checksum = checksum_list[i].strip()
        r.sendline(checksum)
    
    response = r.recvuntil(b" Enter consumption array per household:")
    print(response)
    if not response.startswith(b" Enter consumption array per household:"):
        print("Service did not ask for consumption array")

    for i in range(0,3):
       vals = "{} {} {}".format(random.randint(1,1),random.randint(1,1),random.randint(1,1))
       r.sendline(vals.encode())
    
    response = r.recvuntil(b" Enter the initial guess vector:")
    if not response.startswith(b" Enter the initial guess vector:"):
        print("Service did not ask for guess vector")
    
    for i in range(0,3):
       vals = "{}".format(random.randint(1,1))
       r.sendline(vals.encode())
    
    response = r.recvuntil(b"Stopped after:")
    print(response)

def check_flag(ip,port):
    context.timeout = 5
    #context.log_level = logging.DEBUG
    with remote(ip,port) as r:
        response = r.recvuntil(Menu.MENU_END.value)
        if not response:
            print("Could not load initial menu")
        logging.info("Creating user")
        
        res, reason = register_random_user(r)
        print(res)
        username = res
        password = reason

        res, reason = login_user(r,username,password)
        
        logging.info("Creating checksums")
        #create random number of turbines
        turbines = []
        checksums = []
        num_turbines = random.randint(1,7)
        for i in range(0,num_turbines):
            #turbine, checksum
            res, reason = register_turbine(r)
            turbines.append(res)
            checksums.append(reason)
        
        show_turbine_details(r,turbines[0],checksums[0])
        calculate_capacity(r,turbines,checksums)
        
        r.sendline(Menu.EXIT.value)


if __name__ == "__main__":
    check_flag("127.0.0.1","10060")
