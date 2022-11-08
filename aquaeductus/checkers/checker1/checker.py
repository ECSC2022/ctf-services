#!/usr/bin/env python3

import datetime
import gzip
import hashlib
import logging
import random
import string
from typing import Tuple

import numpy as np
import requests
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult
from numpy.random import default_rng

from Network import generate_network
from WeatherReport import generate_weather_report


class WeatherReportChecker(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10041
        self.timeout = 5  # don't forget to set a timeout for every requests you send
        self.flagsecret = 'bf1ca28f4ecccaf2bd1f'  # secret string used to derive credentials (username, password, ...)
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

        # REPORT 1 - Create a garden
        resp = requests.get(f'{self.baseurl}/gardens/create', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create gardens'
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

        garden_id_1 = resp.headers['Location'][resp.headers['Location'].rindex('/') + 1:]

        # REPORT 1 - Upload a weather report w/o parameters
        resp = requests.get(f'{self.baseurl}/gardens/{garden_id_1}/reports', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create reports'
        gen = default_rng(int.from_bytes(user.encode() + b"v1" + hashlib.sha512(user.encode() + b"v1").digest(), 'big'))
        num_params = gen.integers(24, 48)
        report, rands1, rands2 = generate_weather_report(gen, num_params)
        report_flag = report + flag.encode()
        resp = requests.post(f'{self.baseurl}/gardens/{garden_id_1}/reports',
                             data={'date': datetime.date.today().strftime("%Y-%m-%d")}, files={'report': report_flag},
                             cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Upload weather report 1 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot upload weather report'
        if "Upload" in resp.text or "Download" not in resp.text:
            logging.warning('Upload weather report 1 - failed upload')
            return CheckResult.FAULTY, 'cannot upload weather report'

        # REPORT 2 - Create a garden
        resp = requests.get(f'{self.baseurl}/gardens/create', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create gardens'
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

        garden_id_2 = resp.headers['Location'][resp.headers['Location'].rindex('/') + 1:]

        # REPORT 2 - Upload a weather report w/ parameters
        resp = requests.get(f'{self.baseurl}/gardens/{garden_id_2}/reports', cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Gardens - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot create reports'
        gen = default_rng(int.from_bytes(user.encode() + b"v2" + hashlib.sha512(user.encode() + b"v2").digest(), 'big'))
        num_params = gen.integers(24, 36)
        report, rands1, rands2 = generate_weather_report(gen, num_params, has_extra_params=True)
        report_flag = report + flag.encode()
        resp = requests.post(f'{self.baseurl}/gardens/{garden_id_2}/reports',
                             data={'date': datetime.date.today().strftime("%Y-%m-%d")}, files={'report': report_flag},
                             cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Upload weather report 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot upload weather report'
        if "Upload" in resp.text or "Download" not in resp.text:
            logging.warning('Upload weather report 2 - failed upload')
            return CheckResult.FAULTY, 'cannot upload weather report'

        checkerlib.set_flagid(f'{garden_id_1}:{garden_id_2}')

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        # Network with normal input
        rng = default_rng()
        cookies, garden_id = self._register_user_garden(rng)
        net1, expected_outs = generate_network(rng)
        net1_gzip = gzip.compress(net1.encode())
        resp = requests.post(f"{self.baseurl}/gardens/{garden_id}/infer", files={'network': net1_gzip}, cookies=cookies,
                             timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Network 1 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot infer'

        # Does the response make sense. We don't rerun the inference, just check if enough floats are in the output
        try:
            result = resp.json()['result']
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('Network 1 - invalid json: %s', resp.text)
            return CheckResult.FAULTY, 'cannot infer'

        logging.info('Network 1 - Expected %d results', expected_outs)
        logging.info('Network 1 - Actual: %s', result)
        if len(result) != expected_outs:
            logging.warning('Network 1 - Got incorrect output')
            return CheckResult.FAULTY, 'cannot infer'

        # Network with weather input
        rng = default_rng()
        cookies, garden_id = self._register_user_garden(rng)

        seed = rng.integers(2_147_483_647)
        gen = default_rng(seed)
        num_params = gen.integers(24, 36)
        report, rands1, rands2 = generate_weather_report(gen, num_params, has_extra_params=True)
        report_data = report + ''.join(random.choice(string.printable) for _ in range(37)).encode()
        resp = requests.post(f'{self.baseurl}/gardens/{garden_id}/reports',
                             data={'date': datetime.date.today().strftime("%Y-%m-%d")}, files={'report': report_data},
                             cookies=cookies, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Upload weather report 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot upload weather report'
        if "Upload" in resp.text or "Download" not in resp.text:
            logging.warning('Upload weather report 2 - failed upload')
            return CheckResult.FAULTY, 'cannot upload weather report'

        net2, expected_outs = generate_network(default_rng(seed), "ReportData", num_params, weather_layer_extra=True)
        net2_gzip = gzip.compress(net2.encode())
        resp = requests.post(f"{self.baseurl}/gardens/{garden_id}/infer", files={'network': net2_gzip}, cookies=cookies,
                             timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Network 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot infer'

        try:
            result = resp.json()['result']
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('Network 2 - invalid json: %s', resp.text)
            return CheckResult.FAULTY, 'cannot infer'

        logging.info('Network 2 - Expected %d results', expected_outs)
        logging.info('Network 2 - Actual: %s', result)
        if len(result) != expected_outs:
            logging.warning('Network 2 - Got incorrect output')
            return CheckResult.FAULTY, 'cannot infer'

        return CheckResult.OK, ''

    def _register_user_garden(self, rng):
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

        return cookies, garden_id

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag, owner_user, owner_pw = self.generate_credentials(tick)

        garden_ids_str = checkerlib.get_flagid(tick)
        if not garden_ids_str:
            logging.info('No flagid saved for this team and tick')
            return CheckResult.FLAG_NOT_FOUND, 'flag was not placed successfully'
        garden_ids = garden_ids_str.split(':')

        # Login as garden owner
        resp = requests.post(f'{self.baseurl}/login', data={'username': owner_user, 'password': owner_pw},
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Login - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot login'
        if resp.headers['Location'] != '/':
            logging.warning('Login - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot login'

        cookies_owner = resp.cookies.get_dict()

        # REPORT 1 - Download report as owner
        gen = default_rng(
            int.from_bytes(owner_user.encode() + b"v1" + hashlib.sha512(owner_user.encode() + b"v1").digest(), 'big'))
        num_params1 = gen.integers(24, 48)
        report1, rands11, rands12 = generate_weather_report(gen, num_params1)
        report1flag = report1 + flag.encode()

        resp = requests.get(f'{self.baseurl}/gardens/{garden_ids[0]}/reports/download', cookies=cookies_owner,
                            timeout=self.timeout, stream=True)
        if resp.status_code != 200:
            logging.warning('Report Download 1 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot retrieve report'
        if resp.content != report1flag:
            logging.warning('Report Download 1 - Invalid body')
            return CheckResult.FAULTY, 'cannot retrieve report'

        # REPORT 2 - Download report as owner
        gen = default_rng(
            int.from_bytes(owner_user.encode() + b"v2" + hashlib.sha512(owner_user.encode() + b"v2").digest(), 'big'))
        num_params2 = gen.integers(24, 36)
        report2, rands21, rands22 = generate_weather_report(gen, num_params2, has_extra_params=True)
        report2flag = report2 + flag.encode()

        resp = requests.get(f'{self.baseurl}/gardens/{garden_ids[1]}/reports/download', cookies=cookies_owner,
                            timeout=self.timeout, stream=True)
        if resp.status_code != 200:
            logging.warning('Report Download 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot retrieve report'
        if resp.content != report2flag:
            logging.warning('Report Download 2 - Invalid body')
            return CheckResult.FAULTY, 'cannot retrieve report'

        # Register a new user 1
        user1 = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        pw1 = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        resp = requests.post(f'{self.baseurl}/register', data={'username': user1, 'password': pw1},
                             allow_redirects=False,
                             timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Registration 1 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot register'
        if resp.headers['Location'] != '/':
            logging.warning('Registration 1 - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot register'

        cookies_user1 = resp.cookies.get_dict()
        if 'session' not in cookies_user1:
            logging.warning('Registration 1 - Missing session')
            return CheckResult.FAULTY, 'cannot register'

        # REPORT 1 - Weather layer
        network1 = "\n".join(
            [
                "InputLayer linear",
                str(num_params1),
            ]
            +
            ["InputNode 0"] * num_params1
            +
            [
                "",
                "WeatherLayer linear",
                str(num_params1),
            ]
            +
            ["InputNode 0"] * num_params1
            +
            [
                "ReportData",
                "",
            ]
        )
        network1_gzip = gzip.compress(network1.encode())
        resp = requests.post(f'{self.baseurl}/gardens/{garden_ids[0]}/infer', files={'network': network1_gzip},
                             cookies=cookies_user1,
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Weather infer 1 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot infer'

        try:
            result = resp.json()['result']
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('Weather infer 1 - invalid json')
            return CheckResult.FAULTY, 'cannot infer'

        npresult = np.array(result)
        logging.info('Weather infer 1 - Expected: %s', npresult)
        logging.info('Weather infer 1 - Actual: %s', rands11)
        if not np.allclose(npresult, rands11):
            logging.info('Weather infer 1 - Response: %s', resp.text)
            logging.warning('Weather infer 1 - Incorrect data')
            return CheckResult.FAULTY, 'cannot infer'

        # Register a new user 2
        user2 = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        pw2 = ''.join(random.choice('0123456789abcdef') for _ in range(20))
        resp = requests.post(f'{self.baseurl}/register', data={'username': user2, 'password': pw2},
                             allow_redirects=False,
                             timeout=self.timeout)
        if resp.status_code != 302:
            logging.warning('Registration 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot register'
        if resp.headers['Location'] != '/':
            logging.warning('Registration 2 - Got incorrect redirect %s', resp.headers['Location'])
            return CheckResult.FAULTY, 'cannot register'

        cookies_user2 = resp.cookies.get_dict()
        if 'session' not in cookies_user2:
            logging.warning('Registration 2 - Missing session')
            return CheckResult.FAULTY, 'cannot register'

        # REPORT 2 - Weather layer
        network2 = "\n".join(
            [
                "InputLayer linear",
                str(num_params2),
            ]
            +
            ["InputNode 0"] * num_params2
            +
            [
                "",
                "WeatherLayer explu",
                str(num_params2),
            ]
            +
            ["InputNode 0"] * num_params2
            +
            [
                "ReportData",
                "",
            ]
        )
        network2_gzip = gzip.compress(network2.encode())
        resp = requests.post(f'{self.baseurl}/gardens/{garden_ids[1]}/infer', files={'network': network2_gzip},
                             cookies=cookies_user2,
                             allow_redirects=False, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Weather infer 2 - Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'cannot infer'

        try:
            result = resp.json()['result']
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('Weather infer 2 - invalid json')
            return CheckResult.FAULTY, 'cannot infer'

        npresult = np.array(result)
        expected = rands22 * np.expm1(rands21)
        logging.info('Weather infer 2 - Expected: %s', npresult)
        logging.info('Weather infer 2 - Actual: %s', expected)
        if not np.allclose(npresult, expected):
            logging.info('Weather infer 2 - Response: %s', resp.text)
            logging.warning('Weather infer 2 - Incorrect data')
            return CheckResult.FAULTY, 'cannot infer'

        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(WeatherReportChecker)
