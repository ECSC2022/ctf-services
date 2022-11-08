#!/usr/bin/env python3
import base64
import hashlib
import logging
import random
import string
from base64 import b64encode
from io import BytesIO
from typing import Tuple
import json

import requests
from PIL import Image, ImageDraw
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


class BackendNodeChecker(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10070
        self.timeout = 5  # don't forget to set a timeout for every request you send
        self.flagsecret = '1d04c604c10a00b302b785b8583497c9d41597fe'  # secret string used to derive credentials (username, password, ...)
        self.baseurl = f'http://{self.ip}:{self.port}'

    def generate_credentials(self, tick):
        ''' derive deterministic (but secret) credentials from the flag '''
        flag = checkerlib.get_flag(tick)
        h = hashlib.sha256((flag + self.flagsecret).encode('latin-1')).hexdigest()
        user = 'bot1_' + h[0:20]
        pw = h[20:40]
        return flag, user, pw

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag, user, pw = self.generate_credentials(tick)

        resp = requests.post(f'{self.baseurl}/auth/register',
                             json={"username": user, "hashedPassword": pw, "passport": self.get_passport_data(tick)}, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code when registering %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'couldn\'t register'

        resp = requests.post(f'{self.baseurl}/auth/login', json={"username": user, "hashedPassword": pw}, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code when logging in %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'couldn\'t login'

        try:
            resp_json = resp.json()
            checkerlib.set_flagid(resp_json["userId"])
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('could not decode json response')
            return CheckResult.FLAG_NOT_FOUND, 'no json response'

        token = resp_json["token"]

        telephone_number, address = generate_random_profile_data()

        profile_data = {
            'displayname': user,
            'address': address,
            'isAddressPublic': False,
            'telephoneNumber': telephone_number,
            'isTelephoneNumberPublic': False,
            'status': flag,
            'isStatusPublic': False
        }

        resp = requests.post(f'{self.baseurl}/profile/', json=profile_data, timeout=self.timeout, headers={"Authorization": "Bearer "+token})

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, f"profile incorrect status code"

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        session = requests.session()
        session.headers.update({"User-Agent": "python-requests/"+random.choice(["2.28.1", "2.28.0", "2.27.1", "2.27.0", "2.26.0", "2.25.1"])})

        # check if frontend available
        resp = session.get(f'{self.baseurl}/', timeout=self.timeout)

        if resp.status_code != 200:
            logging.info('Got incorrect status code %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, f"frontend has incorrect status code"

        user, pw = generate_random_login()

        resp = session.post(f'{self.baseurl}/auth/register',
                                 json={"username": user, "hashedPassword": pw, "passport": generate_random_passport()}, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code when registering %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, f"couldn\'t register"

        resp = requests.post(f'{self.baseurl}/auth/login', json={"username": user, "hashedPassword": pw}, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code when logging in %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, f"couldn\'t login"

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('could not decode json response')
            return CheckResult.FLAG_NOT_FOUND, f"login no json response"

        token = resp_json["token"]
        session.headers.update({"Authorization": "Bearer "+token})

        checked_actions = self.choose_executed_actions(n=random.randint(8, 10))
        for action in checked_actions:
            result, error = action(session)
            if result != CheckResult.OK:
                return result, error

        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag, user, pw = self.generate_credentials(tick)

        resp = requests.post(f'{self.baseurl}/auth/login', json={"username": user, "hashedPassword": pw}, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code when logging in %s \n %s', resp.status_code, resp.text)
            return CheckResult.FLAG_NOT_FOUND, f"couldn\'t login"

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('could not decode json response')
            return CheckResult.FLAG_NOT_FOUND, f"login no json response"

        token = resp_json["token"]

        resp = requests.get(f'{self.baseurl}/profile/', timeout=self.timeout, headers={"Authorization": "Bearer "+token})

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while requesting profile %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code'

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.exception('could not decode json response')
            return CheckResult.FAULTY, 'no json response'

        logging.info('Got response %s', resp_json)

        if "status" not in resp_json or resp_json["status"] != flag:
            logging.warning('Got incorrect json %s', resp_json)
            return CheckResult.FLAG_NOT_FOUND, 'flag not found in response'

        return CheckResult.OK, ''

    def get_passport_data(self, tick: int) -> str:
        _, user, _ = self.generate_credentials(tick)

        image = Image.new('RGB', (400, 30), (0, 0, 0))
        d = ImageDraw.Draw(image)
        d.text((10, 10), f'This is the passport of {user}')
        image_out = BytesIO()
        image.save(image_out, 'png')
        return b64encode(image_out.getvalue()).decode()

    def update_profile(self, session) -> Tuple[CheckResult, str]:
        user = self.decode_token_from_session(session)

        telephone, address = generate_random_profile_data()
        profile = {
            "displayname": user["username"].upper() if random.random() < 0.5 else user["username"].lower(),
            "address": address,
            "telephoneNumber": telephone,
            "status": "".join([random.choice(string.hexdigits) for _ in range(random.randint(10, 15))]),
            "isAddressPublic": random.random() < 0.5,
            "isTelephoneNumberPublic": random.random() < 0.5,
            "isStatusPublic": random.random() < 0.5,
        }

        resp = session.post(f'{self.baseurl}/profile/', json=profile, timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s while updating profile information \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while updating profile information'

        return CheckResult.OK, ""

    def fetch_own_profile(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/profile/', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def fetch_profile_by_id(self, session) -> Tuple[CheckResult, str]:
        user = self.decode_token_from_session(session)
        resp = session.get(f'{self.baseurl}/profile/{user["userId"]}', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while fetching profile'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def request_offer(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/offer/', timeout=self.timeout)

        try:
            offers = resp.json()
            if len(offers) == 0:
                return CheckResult.OK, ""
            offer_id = offers[0]["id"]
        except:
            return CheckResult.FAULTY, ""

        resp = session.post(f'{self.baseurl}/request/{offer_id}', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while submitting request %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while submitting request'

        return CheckResult.OK, ""

    def get_requests_by_others(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/request/others', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while fetching requests from other %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while requesting requests from others'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def get_requests_by_me(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/request/me', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while fetching own requests %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while fetching own requests'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def get_offers(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/offer/', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while fetching offers %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while fetching offers'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def get_offers_by_me(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/offer/me', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while fetching own offers %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while fetching own offers'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'

        return CheckResult.OK, ""

    def get_offer_details_by_id(self, session) -> Tuple[CheckResult, str]:
        resp = session.get(f'{self.baseurl}/offer/', timeout=self.timeout)

        try:
            offers = resp.json()
            if len(offers) == 0:
                return CheckResult.OK, ""
            offer = random.choice(offers)
            offer_id = offer["id"]
        except:
            return CheckResult.FAULTY, ""

        resp = session.get(f'{self.baseurl}/offer/{offer_id}', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while fetching offer details %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while fetching offer details'

        try:
            resp.json()
        except:
            return CheckResult.FAULTY, 'no json response'


        return CheckResult.OK, ""

    def add_new_offer(self, session) -> Tuple[CheckResult, str]:
        resp = session.post(f'{self.baseurl}/offer', json=generate_random_offer(), timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while adding new offer %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while adding new offer'

        return CheckResult.OK, ""

    def delete_offer(self, session) -> Tuple[CheckResult, str]:
        session.post(f'{self.baseurl}/offer/', json=generate_random_offer(), timeout=self.timeout)
        resp = session.get(f'{self.baseurl}/offer/me', timeout=self.timeout)

        try:
            offer = resp.json()[0]
            offer_id = offer["id"]
        except:
            return CheckResult.FAULTY, ""

        resp = session.delete(f'{self.baseurl}/offer/{offer_id}', timeout=self.timeout)

        if resp.status_code != 200:
            logging.warning('Got incorrect status code while deleting offer %s \n %s', resp.status_code, resp.text)
            return CheckResult.FAULTY, 'incorrect status code while deleting offer'

        return CheckResult.OK, ""

    def choose_executed_actions(self, n=10):
        available_actions = {self.update_profile, self.fetch_own_profile, self.fetch_profile_by_id, self.request_offer,
                             self.get_requests_by_others, self.get_requests_by_me,  self.get_offers,
                             self.get_offers_by_me, self.get_offer_details_by_id, self.add_new_offer, self.delete_offer}
        chosen_actions = []
        for _ in range(n):
            chosen_action = random.choice(list(available_actions))
            available_actions.remove(chosen_action)
            chosen_actions.append(chosen_action)
        return chosen_actions

    def decode_token_from_session(self, session) -> dict:
        token = session.headers["Authorization"].split(" ")[1]
        _, payload, _ = token.split(".")
        decoded = json.loads(base64.b64decode(payload+'==='))
        return decoded["user"]


def generate_random_profile_data() -> Tuple[str, str]:
    telephone_number = "+" + "".join([str(random.randint(0, 9)) for _ in range(12)])
    street = random.choice(string.ascii_uppercase) + "".join(
        [random.choice(string.ascii_lowercase) for _ in range(random.randint(3, 5))]) + "street"
    street_number = str(random.randint(1, 512))
    if random.random() < 0.5:
        street_number += "/" + str(random.randint(1, 25))

    return telephone_number, street + " " + street_number


def generate_random_login() -> Tuple[str, str]:
    username_alphabet = random.choice([string.ascii_uppercase, string.ascii_lowercase, string.digits])
    password_alphabet = random.choice([string.ascii_uppercase, string.ascii_lowercase]) + string.digits

    username = "".join([random.choice(username_alphabet) for _ in range(random.randint(10, 15))])
    password = "".join([random.choice(password_alphabet) for _ in range(random.randint(10, 25))])

    return username, password


def generate_random_gadget_name() -> str:
    names = [
        "Barium landing barriers processor",
        "Cadmium landing thrusters anchor",
        "Chromium magnesium fetcher",
        "Optronic bubble node lubricator bug-finder",
        "Osmium vacuum glitch-finder",
        "Starboard teleporter sander",
        "Thera-magnetic gluon housing lubriator detonator",
        "Kryptonian neogenic encoder",
        "Gallium polar replicator utensil",
        "Caesium core booster degreaser",
        "Ram landing cushion belt",
        "Triolic bubble repeller timer",
        "Graviton rubidium generator polisher",
        "Boron flinger acid",
        "Phaser containment field detonator",
        "Rear-side antigravity device",
        "Starboard gluon bio-tubing bug-finder",
        "Nitrogen electro-plasma portal drive pack",
        "Kryptonian ion washer",
        "Nanowave gamma-wave drive pedal",
        "Promethean antigravity sled",
        "Chromium solar sails mopper",
        "Gold-plated propeller shifter",
        "Grease resistant wave drive plates greaser",
        "Germanium glob propeller housing mop",
        "Faulty carbon ram washer",
        "Tantulum wave cleaner",
        "Manganese housing locator",
        "Quantum shift generator blower",
        "Hyper sensitive ram belt",
        "Port phaser housing lubriator plug",
        "Chlorine replicator glitch-finder",
        "Deltonium caesium landing brackets spooler",
        "Promethean bubble extender",
        "Front power setter",
        "Molecular fragmentor welder",
        "Primary and auxiliary power flinger repeller",
        "Subatomic drive pedals setter",
        "Nitronium vacuum impulser recorder",
        "Positronic electro-ceramic ramscoop adjuster",
        "Barium polar autosequencer",
        "Sulfur electro-plasma scrubber",
        "Germanium portal generator settler",
        "Mercury crystal acid",
        "Hyper sensitive turbine mopper",
        "Lithium microfilament anchor",
        "Chrome charge teleporter freezer",
        "Cadmium microfilament welder",
        "Iridium alloy caesium bio-tubing fastener",
        "Iridium alloy pulse impulser gilder",
        "Nitrogen antigravity heater",
        "Backup portal generator adjuster",
        "Isotopic phaser casing encoder",
        "Nitrogen ray emergency rocket fragmentor",
        "Chromium FTL glitch-nullifier",
        "Tritonic ray connector",
        "Gamma ion spore-housing cleaner",
        "Mercury drive grease cleaner",
        "Mercury antigravity flinger generator",
        "Port containment converter sled",
        "Manganese gluon crystal core container",
        "Germanium delta-wave propulsion nullifyer implaner",
        "Gamma-wave teleporter cruncher",
        "Iridium alloy gluon propulsion converter"
    ]

    return random.choice(names)


def generate_random_description_start() -> str:
    description_starts = [
        "I offer my ",
        "Found this ",
        "Brand new ",
        "No 'whats last price?' questions!\n\n",
        "In top condition\n"
    ]
    return random.choice(description_starts)


def generate_random_offer() -> dict:
    name = generate_random_gadget_name()
    return {
        "name": name,
        "description": generate_random_description_start() + name
    }


def generate_random_passport():
    def random_word():
        chars = "".join([random.choice(string.ascii_lowercase) for _ in range(random.randint(2, 5))])
        if random.random() < 0.5:
            chars = random.choice(string.ascii_uppercase) + chars
        return chars

    phrase = " ".join([random_word() for _ in range(random.randint(4, 7))])

    image = Image.new('RGB', (400, 30), (0, 0, 0))
    d = ImageDraw.Draw(image)
    d.text((10, 10), phrase)
    image_out = BytesIO()
    image.save(image_out, 'png')
    return b64encode(image_out.getvalue()).decode()


if __name__ == '__main__':
    checkerlib.run_check(BackendNodeChecker)
