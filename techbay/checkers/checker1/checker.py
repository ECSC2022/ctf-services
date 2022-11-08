#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import base64
from io import BytesIO
from hashlib import sha256
from typing import Tuple

import hashlib
import logging
import random
import socket

import requests
from requests.structures import CaseInsensitiveDict
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

REQUESTS_VERSIONS = [
    "2.28.1", 
    "2.28.0", 
    "2.27.1", 
    "2.27.0", 
    "2.26.0", 
    "2.25.1",
    "2.25.0",
    "2.24.0",
    "2.23.0",
    "2.22.0",
    "2.21.0",
    "2.20.1",
    "2.20.0"
]


class BackendRustChecker(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10070
        self.timeout = 5 # don't forget to set a timeout for every requests you send
        self.flagsecret = 'ef79514d9c7943858b587b203b00a01c406c40d1' # secret string used to derive credentials (username, password, ...)
        self.baseurl = f'http://{self.ip}:{self.port}'

    def generate_credentials(self, tick):
        ''' derive deterministic (but secret) credentials from the flag '''
        flag = checkerlib.get_flag(tick)
        h = hashlib.sha256((flag + self.flagsecret).encode('latin-1')).hexdigest()
        user = 'bot2_' + h[0:20]
        pw = h[20:40]
        return flag, user, pw

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        session = requests.session()
        session.headers.update({"User-Agent": "python-requests/"+random.choice(REQUESTS_VERSIONS)})
        
        flag, user, pw = self.generate_credentials(tick)
        (img_base64, img_hash) = self.generate_passport(flag)
        params = {'username': user, 'hashedPassword': pw, 'passport': img_base64}
        resp = session.post(f'{self.baseurl}/auth/register', json=params, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        logging.info('Register got response %s', resp.text)

        params = {'username': user, 'hashedPassword': pw}
        resp = session.post(f'{self.baseurl}/auth/login', json=params, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        try:
            resp_json = resp.json()
            # set the flagid as soon as the flag has been placed
            checkerlib.set_flagid(resp_json['userId'])
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('coult not decode json response')
            return CheckResult.FAULTY, 'no json response'

        logging.info('Login got response %s', resp_json)

        if resp_json['username'] != user:
            logging.warning('Got incorrect json: %s', resp_json)
            return CheckResult.FAULTY, 'incorrect json response'

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        session = requests.session()
        session.headers.update({"User-Agent": "python-requests/"+random.choice(REQUESTS_VERSIONS)})
        resp = session.get(self.baseurl, timeout=self.timeout)

        if resp.status_code != 200:
            logging.info('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'
        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        session = requests.session()
        session.headers.update({"User-Agent": "python-requests/"+random.choice(REQUESTS_VERSIONS)})
        flag, user, pw = self.generate_credentials(tick)
        params = {'username': user, 'hashedPassword': pw}
        resp = session.post(f'{self.baseurl}/auth/login', json=params, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FLAG_NOT_FOUND, 'incorrect status code'

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('coult not decode json response')
            return CheckResult.FLAG_NOT_FOUND, 'no json response'

        logging.info('Got response %s', resp_json)
        
        h = sha256()
        h.update(resp_json["passport"].encode())
        passport_hash = h.digest()

        flag_image = base64.b64decode(resp_json["passport"])
        img = Image.open(BytesIO(flag_image))


        (img_base64, img_hash) = self.generate_passport(flag)

        if img_hash != passport_hash or img.info['author'] != flag:
            logging.warning('Got incorrect flag in json %s', resp_json)
            return CheckResult.FLAG_NOT_FOUND, 'flag not found in response'
        

        return CheckResult.OK, ''

    def generate_passport(self, flag):
        img = Image.new('RGB', (4000, 200), color = (0, 0, 0))

        metadata = PngInfo()
        metadata.add_text("author", flag)

        font = ImageFont.truetype("Inconsolata-Regular.ttf", size=130)
        
        d = ImageDraw.Draw(img)
        d.text((10,50), flag, fill=(255,255,255), font=font)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG", pnginfo=metadata)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        h = sha256()
        h.update(img_base64.encode())
        img_hash = h.digest()
        return (img_base64, img_hash)


if __name__ == '__main__':
    checkerlib.run_check(BackendRustChecker)
