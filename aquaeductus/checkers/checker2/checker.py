#!/usr/bin/env python3
import base64
import gzip
import hashlib
import logging
import random
from typing import Tuple

import requests
from bs4 import BeautifulSoup
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult
from numpy.random import default_rng


class GardenChecker(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10041
        self.timeout = 5  # don't forget to set a timeout for every requests you send
        self.flagsecret = '5a7fd06d1aca73e913de'  # secret string used to derive credentials (username, password, ...)
        self.baseurl = f'http://{self.ip}:{self.port}'

    def generate_credentials(self, tick: int):
        ''' derive deterministic (but secret) credentials from the flag '''
        flag = checkerlib.get_flag(tick)
        h = hashlib.sha256((flag + self.flagsecret).encode('latin-1')).hexdigest()
        user = h[0:20]
        pw = h[20:40]
        return flag, user, pw

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag, user, pw = self.generate_credentials(tick)
        rng = default_rng()

        # Register a new user
        logging.warning(self.baseurl)
        resp = requests.post(f'{self.baseurl}/register', data={'username': user, 'password': pw}, allow_redirects=False,
                             timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Registration - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot register'
        if resp.headers['Location'] != '/':
            logging.warning('Registration - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot register'

        cookies = resp.cookies.get_dict()
        if 'session' not in cookies:
            logging.warning('Registration - Missing session')
            return CheckResult.FAULTY, 'cannot register'

        # Act human
        resp = requests.get(f'{self.baseurl}/gardens', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot view gardens'
        resp = requests.get(f'{self.baseurl}/gardens/create', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create gardens'

        # Create a garden
        resp = requests.post(f'{self.baseurl}/gardens', data={
            'name': ''.join(random.choice('0123456789abcdef') for _ in range(20)),
            'latitude': rng.integers(0, 160) - 80 + round(rng.random(), 3),
            'longitude': rng.integers(0, 340) - 170 + round(rng.random(), 3),
            'water_required': rng.integers(1, 360),
            'instructions': flag,
        }, cookies=cookies, allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Garden creation - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'
        if 'Location' not in resp.headers:
            logging.warning('Garden creation - Got incorrect redirect', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'

        garden_id = resp.headers['Location'][resp.headers['Location'].rindex('/') + 1:]
        checkerlib.set_flagid(garden_id)

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        rng = default_rng()

        # Register a new user
        user = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        pw = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        resp = requests.post(f'{self.baseurl}/register', data={'username': user, 'password': pw}, allow_redirects=False,
                             timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Registration - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot register'
        if resp.headers['Location'] != '/':
            logging.warning('Registration - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot register'

        cookies = resp.cookies.get_dict()
        if 'session' not in cookies:
            logging.warning('Registration - Missing session')
            return CheckResult.FAULTY, 'cannot register'

        # Create a garden
        latitude = rng.integers(0, 89) + round(rng.random(), 3)
        longitude = rng.integers(0, 179) + round(rng.random(), 3)
        resp = requests.post(f'{self.baseurl}/gardens', data={
            'name': ''.join(random.choice('0123456789abcdef') for _ in range(20)),
            'latitude': latitude,
            'longitude': longitude,
            'water_required': rng.integers(1, 1000),
            'instructions': ''.join(random.choice('0123456789abcdef') for _ in range(rng.integers(10, 120))),
        }, cookies=cookies, allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Garden creation - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'
        if 'Location' not in resp.headers:
            logging.warning('Garden creation - Got incorrect redirect', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'

        garden_id = resp.headers['Location'][resp.headers['Location'].rindex('/') + 1:]

        # Check coordinates layer
        network = "\n".join([
            "InputLayer linear",
            "2",
            "InputNode 0",
            "InputNode 0",
            "",
            "LocationLayer linear",
            "2",
            "RetrievalNode Latitude",
            "RetrievalNode Longitude",
            "",
            "",
        ])
        network_gzip = gzip.compress(network.encode())
        resp = requests.post(f'{self.baseurl}/gardens/{garden_id}/infer', files={'network': network_gzip},
                             cookies=cookies,
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Location infer - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot infer'

        try:
            js = resp.json()
            result = js['result']
            stdout = js['stdout']
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('Location infer - invalid json')
            return CheckResult.FAULTY, 'cannot infer'

        if result != [latitude, longitude]:
            logging.warning('Location infer - Incorrect data: %s', resp.text)
            return CheckResult.FAULTY, 'cannot infer'

        logs = gzip.decompress(
            base64.b64decode(stdout.replace('_', '/').replace('-', '+').encode() + b'=' * (-len(stdout) % 4))
        ).decode()

        if 'found layer InputLayer with 2 nodes' not in logs or 'found layer LocationLayer with 2 nodes' not in logs or 'declares InputNode' not in logs or 'parsing from line' not in logs or 'declares RetrievalNode' not in logs:
            logging.warning('Location infer - Incorrect logs: %s', logs)
            return CheckResult.FAULTY, 'invalid infer logs'

        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag, owner_user, owner_pw = self.generate_credentials(tick)
        rng = default_rng()

        garden_id = checkerlib.get_flagid(tick)
        if not garden_id:
            logging.info('No flagid saved for this team and tick')
            return CheckResult.FLAG_NOT_FOUND, 'flag was not placed successfully'

        # Register a new user
        user = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        pw = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        resp = requests.post(f'{self.baseurl}/register', data={'username': user, 'password': pw}, allow_redirects=False,
                             timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Registration - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot register'
        if resp.headers['Location'] != '/':
            logging.warning('Registration - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot register'

        cookies = resp.cookies.get_dict()
        if 'session' not in cookies:
            logging.warning('Registration - Missing session')
            return CheckResult.FAULTY, 'cannot register'

        # Make a garden watering request
        resp = requests.get(f'{self.baseurl}/gardens/{garden_id}', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Garden View - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot find garden'

        resp = requests.get(f'{self.baseurl}/gardens/{garden_id}/watering', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Garden Watering - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot find garden'

        resp = requests.post(f'{self.baseurl}/gardens/{garden_id}/watering', data={
            'water_available': rng.integers(1, 1000),
        }, cookies=cookies, allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Garden creation - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'
        if 'Location' not in resp.headers:
            logging.warning('Garden creation - Got incorrect redirect', resp.status_code)
            return CheckResult.FAULTY, 'cannot create garden'

        try:
            request_id_str = resp.headers['Location'][resp.headers['Location'].rindex('#request-') + 9:]
            if not request_id_str.isdigit():
                logging.info('location does not have request id: %s', resp.headers['Location'])
                return CheckResult.FAULTY, 'request not returned'
            request_id = int(request_id_str)
        except ValueError as e:
            logging.info('location does not have request id (%s): %s', e, resp.headers['Location'])
            return CheckResult.FAULTY, 'request not returned'

        # Login as garden owner
        resp = requests.post(f'{self.baseurl}/login', data={'username': owner_user, 'password': owner_pw},
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Login - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot login'
        if resp.headers['Location'] != '/':
            logging.warning('Login - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot login'

        owner_cookies = resp.cookies.get_dict()

        # Approve watering request
        resp = requests.post(f'{self.baseurl}/gardens/{garden_id}/watering/{request_id}', cookies=owner_cookies,
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Watering request approval - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot approve request'
        if resp.headers['Location'] != f'/gardens/{garden_id}/watering':
            logging.warning('Watering approval - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot approve request'

        # Retrieve flag
        resp = requests.get(f'{self.baseurl}/gardens/{garden_id}/watering', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Garden Watering - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot find garden'

        soup = BeautifulSoup(resp.text, 'html.parser')
        instructions = soup.find(id=f"request{request_id}_instructions")
        if instructions is None:
            logging.warning('Garden Watering - Instructions not found')
            return CheckResult.FLAG_NOT_FOUND, 'cannot find flag'

        if flag not in instructions.contents[0]:
            logging.warning('Garden Watering - Flag not found')
            return CheckResult.FLAG_NOT_FOUND, 'cannot find flag'

        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(GardenChecker)
