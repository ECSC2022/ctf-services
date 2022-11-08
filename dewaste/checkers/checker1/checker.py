#!/usr/bin/env python3
import abc
import string
import urllib.parse
from abc import abstractmethod

from bs4 import BeautifulSoup
from faker import Faker
import hashlib
import logging
import random
import re
import time
from typing import Tuple, Dict, Optional, Union, List, Callable

import requests
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

# secret string used to derive credentials (username, password, ...)
FLAG_SECRET = "9ToQ11yCMGEEAfn6IXwSQHIxQrUvNRVtDM9zRG3C1yrK9g6igV1R0puQfuffH6lR"
# the length of the item id is restricted because it is used in the flagid
MAX_ITEM_ID = 100000000


def get_random_useragent() -> str:
    requests_versions = [
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
    return "python-requests/" + random.choice(requests_versions)


def random_chars(len: int, charset: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890") -> str:
    return "".join(random.choices(charset, k=len))


def sha256(content: Union[str, bytes]) -> str:
    if type(content) == str:
        content = content.encode('latin-1')
    return hashlib.sha256(content).hexdigest()


class FileGenerator(abc.ABC):
    @abstractmethod
    def generate(self, flag: str) -> Tuple[bytes, str]:
        """Generates a new file with the flag somewhere inside. Returns the content and the file extension."""
        pass


class StaticFileGenerator(FileGenerator):
    def __init__(self, content: bytes, ext: str) -> None:
        super().__init__()
        self.content = content
        self.ext = ext

    def generate(self, flag: str) -> Tuple[bytes, str]:
        return self.content, self.ext


class TextFileGenerator(FileGenerator):
    exts = ['txt', 'md']

    def generate(self, flag: str) -> Tuple[bytes, str]:
        content = flag.encode('latin-1')
        file_ext = random.choice(self.exts)
        return content, file_ext


class ImageFileGenerator(FileGenerator):
    exts = ['png', 'jpeg', 'gif', 'jpg']

    def _randcolor(self):
        return tuple([random.randint(0, 256) for _ in range(3)])

    def generate(self, flag: str) -> Tuple[bytes, str]:
        import io
        from PIL import Image, ImageDraw, ImageFont
        from PIL.PngImagePlugin import PngInfo

        import os
        dirname = os.path.dirname(__file__)
        font_filepath = os.path.join(dirname, 'dejavu.ttf')

        font_height = 11 #manually measured at font-size 14
        txt = flag
        file_ext = random.choice(self.exts)
        img_width, img_height = [random.randint(330, 350), random.randint(20, 40)]
        # stick to dejavu mono as a font
        fnt = ImageFont.truetype(font_filepath, 14)
        # pick a random color as background
        img = Image.new('RGB', (img_width, img_height), self._randcolor())
        draw = ImageDraw.Draw(img)
        # fg color is always black
        txt_length = draw.textlength(txt, font=fnt)
        draw.text(
            (
                (img_width - txt_length)//2,
                (img_height - font_height)//2
            ),
            txt, fill=(0,0,0), font=fnt)
        fh = io.BytesIO()
        if file_ext == 'gif':
            attrs = {'format': 'GIF', 'comment': txt}
        elif file_ext == 'png':
            png_metadata = PngInfo()
            png_metadata.add_text('flg', txt)
            attrs = {'format': 'PNG', 'pnginfo': png_metadata, 'compress_level': 9}
        else:
            attrs = {'format': 'JPEG', 'exif': txt.encode('latin-1'), 'quality': 75}
        img.save(fh, **attrs)

        return fh.getvalue(), file_ext


class TarFileGenerator(FileGenerator):

    def __init__(self, file_gen: FileGenerator, compression: str = "") -> None:
        super().__init__()
        self.file_gen = file_gen
        valid_modes = ["", "gz", "bz2"]
        if compression not in valid_modes:
            raise ValueError(f"Invalid compression mode '{compression}'. Valid: " + ", ".join(valid_modes))
        self._compression = compression

    def generate(self, flag: str) -> Tuple[bytes, str]:
        import io
        import tarfile

        flag_file, flag_ext = self.file_gen.generate(flag)

        path = ""
        for i in range(random.randint(0, 5)):
            path += random_chars(random.randint(5, 10)) + "/"

        fh = io.BytesIO()
        with tarfile.open(fileobj=fh, mode='w:' + self._compression) as tar:
            info = tarfile.TarInfo(path + 'flag.' + flag_ext)
            info.size = len(flag_file)
            tar.addfile(info, io.BytesIO(flag_file))
        return fh.getvalue(), "tar." + self._compression if self._compression != "" else "tar"


class InteractionHelper:

    def __init__(self, baseurl: str, timeout: int = 10) -> None:
        self.baseurl = baseurl
        self.timeout = timeout
        self.fake = Faker()

    def get_password_by_flag(self, flag: str) -> str:
        """ derive deterministic (but secret) credentials from the flag """
        h = hashlib.sha256((flag + FLAG_SECRET).encode('latin-1')).hexdigest()
        return "Aa1" + h[0:20]  # prefix needed to form a valid password in every case

    def create_flag_user_details(self, flag: str) -> Dict:
        num = random.randint(1000, 9999)
        firstname = self.fake.first_name(max_length=15)
        lastname = self.fake.last_name(max_length=15)
        email = f"{firstname.lower()}.{lastname.lower()}{num}@example.org"
        pw = self.get_password_by_flag(flag)
        return {"email": email, "password": pw, "firstname": firstname, "lastname": lastname}

    def create_physical_item(self) -> Dict:
        return {
            "serial": random_chars(random.randint(20, 30), "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"),
            "item_description": "",
            "length": random.randint(1, 10000),
            "width": random.randint(1, 10000),
            "height": random.randint(1, 10000),
            "weight": random.randint(1, 100),
        }

    def service_login(self, s: requests.Session, email: str, password: str) -> Tuple[CheckResult, str]:
        data = {
            "email": email,
            "password": password
        }
        s.headers.update({"User-Agent": get_random_useragent()})
        resp = s.post(f'{self.baseurl}/user/login', data=data, timeout=self.timeout)
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Login failed: %s %s', email, password)
            return CheckResult.FLAG_NOT_FOUND, 'could not log in'

        if not resp.url.endswith("/recycle/myitems"):
            logging.warning('Got redirected to the wrong url %s', resp.url)
            return CheckResult.FAULTY, 'wrong redirect after login'

        return CheckResult.OK, ''

    def register_physical_item_with_user(self, user: Dict, physical_item: Dict,
                                         session: Optional[requests.Session] = None) \
            -> Tuple[CheckResult, Union[str, requests.Response]]:
        data = {
            **physical_item,
            "auth_type": "account",
            "newEmail": user["email"],
            "newPassword": user["password"],
            "newFirstname": user["firstname"],
            "newLastname": user["lastname"]
        }
        if session is None:
            session = requests
        resp = session.post(
            f'{self.baseurl}/recycle/physical/register',
            data=data,
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        if "Serial number is already registered." in resp.text:
            logging.error('Flag was already stored in the service. Flag dispatcher should not run twice per tick...')
            return CheckResult.FAULTY, 'serial number duplicate'

        if "/recycle/myitems/physical/" not in resp.url:
            logging.warning('Not redirected to the created item, instead: %s', resp.url)
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'incorrect page'

        item_id = self.get_item_id_for_physical_item_link(resp.url)
        if item_id is None:
            logging.warning("Cannot get item_id from url: %s", resp.url)
            return CheckResult.FAULTY, 'could not parse item id'

        if item_id > MAX_ITEM_ID:
            logging.warning("Item Id too long: %s (Maximum = %s)", item_id, MAX_ITEM_ID)
            return CheckResult.FAULTY, 'item id incorrect'

        return CheckResult.OK, resp

    def parse_info_of_physical_item_page(self, page_content: str) -> Tuple[CheckResult, Union[str, Dict]]:
        soup = BeautifulSoup(page_content, 'html.parser')

        dd_list = soup.find_all("dd")
        dd_count = len(dd_list)
        dd_expected_count = 6
        if dd_count != dd_expected_count:
            logging.warning("Invalid number of dd elements on page. Expected %s, but got %s", dd_expected_count,
                            dd_count)
            return CheckResult.FAULTY, 'invalid number of dd elements for physical item'

        serial = dd_list[1].get_text().strip()
        if not serial:
            return CheckResult.FAULTY, "missing serial number"

        dimensions = dd_list[2].get_text().strip()
        m = re.match(r"^(\d+)/(\d+)/(\d+) cm$", dimensions)
        if not m:
            logging.warning("Cannot parse dimensions: %s", dimensions)
            return CheckResult.FAULTY, 'cannot parse item dimensions'

        weight = dd_list[3].get_text().strip()
        m2 = re.match(r"^(\d+(?:\.\d+)?) kg$", weight)
        if not m2:
            logging.warning("Cannot parse weight: %s", weight)
            return CheckResult.FAULTY, 'cannot parse item weight'

        status = dd_list[4].get_text().lower().strip()

        description = dd_list[5].find("pre")
        if not description:
            logging.warning("Missing item description for physical item")
            return CheckResult.FAULTY, "missing item description for physical item"

        return CheckResult.OK, {
            "serial": serial,
            "length": int(m.group(1)),
            "width": int(m.group(2)),
            "height": int(m.group(3)),
            "weight": float(m2.group(1)),
            "status": status,
            "item_description": description.get_text()
        }

    def parse_info_of_digital_item_page(self, page_content: str) -> Tuple[CheckResult, Union[str, Dict]]:
        soup = BeautifulSoup(page_content, 'html.parser')
        dd_list = soup.find_all("dd")
        dd_count = len(dd_list)
        dd_expected_count = 5
        if dd_count != dd_expected_count:
            logging.warning("Invalid number of dd elements on page. Expected %s, but got %s", dd_expected_count,
                            dd_count)
            return CheckResult.FAULTY, 'invalid number of dd elements for digital item'

        name = dd_list[1].get_text().strip()

        description = dd_list[2].find("pre")
        if not description:
            logging.warning("Missing item description for digital item")
            return CheckResult.FAULTY, "missing item description for digital item"

        size = dd_list[3].get_text().strip()
        m2 = re.match(r"^(\d+(?:\.\d+)?) kB$", size)
        if not m2:
            logging.warning("Cannot parse size: %s", size)
            return CheckResult.FAULTY, 'cannot parse item size'

        status = dd_list[4].get_text().lower().strip()

        results = []
        result_list = soup.find_all("div", class_="result")
        for r in result_list:
            title = r.find('p')
            if not title:
                logging.warning("Analysis result has no type", r.get_text())
                return CheckResult.FAULTY, 'analysis result has no type'
            title = title.get_text().strip()
            if title[:6] != "Type: ":
                logging.warning("Analysis result title does not describe type: %s", title)
                return CheckResult.FAULTY, 'analysis result has no type'
            content = r.find('pre')
            if not content:
                logging.warning("Analysis result has no content", r.get_text())
                return CheckResult.FAULTY, 'analysis result has no content'
            results.append({"type": title[6:], "content": content.get_text()})

        return CheckResult.OK, {
            "item_description": description.get_text().strip(),
            "name": name,
            "size": float(m2.group(1)),
            "status": status,
            "results": results
        }

    def service_get_serial_of_physical_item_with_token(self, item_id: int, token: str) -> Tuple[CheckResult, str]:
        """Returns the contents of a physical item page that is accessed with an authentication token"""
        resp = requests.get(f'{self.baseurl}/recycle/myitems/physical/{item_id}?authToken={token}',
                            timeout=self.timeout, headers={'User-Agent': get_random_useragent()})

        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Login failed')
            return CheckResult.FLAG_NOT_FOUND, 'could not log in'

        info = self.parse_info_of_physical_item_page(resp.text)
        if info[0] != CheckResult.OK:
            return info

        return CheckResult.OK, info[1]["serial"]

    def download_digital_item_with_token(self, item_id: int, token: str) -> Tuple[CheckResult, Union[str, bytes]]:
        resp = requests.get(f'{self.baseurl}/recycle/myitems/digital/{item_id}/download?authToken={token}',
                            timeout=self.timeout, headers={'User-Agent': get_random_useragent()})
        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Login failed')
            return CheckResult.FLAG_NOT_FOUND, 'could not log in'

        return CheckResult.OK, resp.content

    def get_ranking(self, session: Optional[requests.Session] = None) -> Tuple[CheckResult, Union[str, List[Dict]]]:
        if session is None:
            session = requests
        resp = session.get(
            f'{self.baseurl}/ranking',
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code for ranking %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code for ranking'

        soup = BeautifulSoup(resp.text, "html.parser")
        tbody = soup.find("tbody")
        if not tbody:
            logging.warning('No table on ranking page')
            return CheckResult.FAULTY, 'no table on ranking page'

        rows = tbody.find_all("tr")
        ret = []
        for row in rows:
            user_id = row["data-user-id"]
            if not user_id:
                logging.warning('User ID missing on ranking table')
                return CheckResult.FAULTY, 'ranking table incorrect'
            columns = row.findChildren('td', recursive=False)
            if len(columns) != 4:
                logging.warning('Unexpected number of columns at ranking table')
                return CheckResult.FAULTY, 'ranking table incorrect'
            email = columns[0]["data-contact"]
            if email is None:
                logging.warning('Missing contact email at ranking table')
                return CheckResult.FAULTY, 'ranking table incorrect'
            fullname = columns[0].get_text().strip()
            total_phys = columns[1].get_text().strip()
            if not total_phys.isnumeric():
                logging.warning('Physical item number at ranking table not a number: %s', total_phys)
                return CheckResult.FAULTY, 'ranking table incorrect'
            total_digital = columns[2].get_text().strip()
            if not total_digital.isnumeric():
                logging.warning('Digital item number at ranking table not a number: %s', total_digital)
                return CheckResult.FAULTY, 'ranking table incorrect'
            ret.append({
                "user_id": user_id,
                "fullname": fullname,
                "email": email,
                "total_phys": int(total_phys),
                "total_digital": int(total_digital)
            })

        return CheckResult.OK, ret

    def get_faq(self, query: str = "") -> Tuple[CheckResult, Union[str, List[Dict]]]:
        if query:
            logging.info("Querying faq page with: %s", query)
        query = "?q=" + urllib.parse.quote_plus(query) if query != "" else ""
        resp = requests.get(
            f"{self.baseurl}/faq{query}",
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code for faq %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code for faq'
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.find_all("div", class_="faq")
        ret = []
        for item in items:
            question = item.find("div", class_="faq-question")
            if not question:
                logging.warning('Question missing from faq item')
                return CheckResult.FAULTY, 'incorrect faq structure'
            answer = item.find("div", class_="faq-answer")
            if not answer:
                logging.warning('Answer missing from faq item')
                return CheckResult.FAULTY, 'incorrect faq structure'
            ret.append({"question": question.get_text(), "answer": answer.get_text()})

        return CheckResult.OK, ret

    def create_digital_item(
            self,
            file_gen: FileGenerator,
            content: Optional[str] = None,
            user: Optional[Dict] = None
    ) -> Dict:
        if content is None:
            content = random_chars(random.randint(10, 40))

        file, ext = file_gen.generate(content)
        file_hash = sha256(file)
        if user:
            filename = user["firstname"].lower() + "_" + user["lastname"].lower() + "." + ext
        else:
            filename = file_hash + "." + ext
        return {
            "item_description": "",
            "content": file,
            "extension": ext,
            "hash": file_hash,
            "name": filename
        }

    def register_digital_item_with_user(
            self,
            user: Dict,
            digital_item: Dict,
            session: Optional[requests.Session] = None
    ) -> Tuple[CheckResult, Union[str, requests.Response]]:
        data = {
            "item_description": digital_item["item_description"],
            "auth_type": "account",
            "newEmail": user["email"],
            "newPassword": user["password"],
            "newFirstname": user["firstname"],
            "newLastname": user["lastname"]
        }
        if session is None:
            session = requests
        resp = session.post(
            f'{self.baseurl}/recycle/digital/upload',
            data=data,
            files={"datafile": (digital_item["name"], digital_item["content"], 'multipart/form-data')},
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        if "/recycle/myitems/digital/" not in resp.url:
            logging.warning('Not redirected to the created item, instead: %s', resp.url)
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'incorrect page'

        item_id = self.get_item_id_for_digital_item_link(resp.url)
        if item_id is None:
            logging.warning("Could not read item id from url: %s", resp.url)
            return CheckResult.FAULTY, 'cannot parse item id'

        if item_id > MAX_ITEM_ID:
            logging.warning("Item Id is too long: %s (Maximum = %s)", item_id, MAX_ITEM_ID)
            return CheckResult.FAULTY, 'wrong item id'

        return CheckResult.OK, resp

    def register_digital_item_anonymous(
            self,
            digital_item: Dict,
            session: Optional[requests.Session] = None
    ) -> Tuple[CheckResult, Union[str, requests.Response]]:
        data = {
            "item_description": digital_item["item_description"],
            "auth_type": "once",
        }
        if session is None:
            session = requests
        resp = session.post(
            f'{self.baseurl}/recycle/digital/upload',
            data=data,
            files={"datafile": (digital_item["name"], digital_item["content"], 'multipart/form-data')},
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        if "Item successfully registered." not in resp.text:
            logging.warning('Item not registered successfully')
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'no successful registration'

        success_box_result = self.parse_success_box_link(resp.text)
        if success_box_result[0] != CheckResult.OK:
            return success_box_result

        item_id, auth_token = success_box_result[1]

        if item_id > MAX_ITEM_ID:
            logging.warning("Item id too large: %s (Maximum = %s)", success_box_result[1][0], MAX_ITEM_ID)
            return CheckResult.FAULTY, 'item id incorrect'

        return CheckResult.OK, resp

    def register_physical_item_anonymous(
            self,
            physical_item: Dict,
            session: Optional[requests.Session] = None
    ) -> Tuple[CheckResult, Union[str, requests.Response]]:
        data = {
            **physical_item,
            "auth_type": "once",
        }
        if session is None:
            session = requests
        resp = session.post(
            f'{self.baseurl}/recycle/physical/register',
            data=data,
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        if "Serial number is already registered." in resp.text:
            logging.error('Flag was already stored in the service. Flag dispatcher should not run twice per tick...')
            return CheckResult.FAULTY, 'item already exists'

        if "Item successfully registered." not in resp.text:
            logging.warning('Item not registered successfully')
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'no successful registration'

        success_box_result = self.parse_success_box_link(resp.text)
        if success_box_result[0] != CheckResult.OK:
            return success_box_result

        item_id, auth_token = success_box_result[1]

        if item_id > MAX_ITEM_ID:
            logging.warning("Item id too large: %s (Maximum = %s)", success_box_result[1][0], MAX_ITEM_ID)
            return CheckResult.FAULTY, 'item id incorrect'

        return CheckResult.OK, resp

    def download_digital_item_with_session(
            self,
            item_id: int,
            s: requests.Session
    ) -> Tuple[CheckResult, Union[str, bytes]]:
        resp = s.get(f'{self.baseurl}/recycle/myitems/digital/{item_id}/download',
                     timeout=self.timeout, headers={'User-Agent': get_random_useragent()})
        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Authentication failed')
            return CheckResult.FLAG_NOT_FOUND, 'could not authenticate'

        return CheckResult.OK, resp.content

    def get_item_id_for_physical_item_link(self, link: str) -> Optional[int]:
        m = re.match(r".*/recycle/myitems/physical/(\d+)", link)
        if not m:
            return None
        return int(m.group(1))

    def get_item_id_for_digital_item_link(self, link: str) -> Optional[int]:
        m = re.match(r".*/recycle/myitems/digital/(\d+)", link)
        if not m:
            return None
        return int(m.group(1))

    def parse_success_box_link(self, page_content: str) -> Tuple[CheckResult, Union[str, Tuple[int, str]]]:
        soup = BeautifulSoup(page_content, 'html.parser')
        msg_box = soup.find('p', class_="alert-success")
        if not msg_box:
            logging.warning('Success box missing on page')
            return CheckResult.FAULTY, 'success message box not found'
        content = msg_box.get_text().strip()

        m = re.search(r"/recycle/myitems/(?:physical|digital)/(\d+)\?authToken=([0-9a-f]{40})", content)
        if not m:
            logging.warning("Cannot find visit link in message box. Got: %s", content)
            return CheckResult.FAULTY, 'item access link in message box not found'

        item_id = int(m.group(1))
        auth_token = m.group(2)
        return CheckResult.OK, (item_id, auth_token)

    def service_logout(self, s: requests.Session) -> Tuple[CheckResult, str]:
        resp = s.get(
            f"{self.baseurl}/user/logout",
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if not resp.url.endswith("/user/login"):
            logging.warning("Was not redirected to login page after logout")
            return CheckResult.FAULTY, 'could not logout'
        return CheckResult.OK, ''

    def register_physical_item_while_logged_in(
            self,
            physical_item: Dict,
            session: requests.Session
    ) -> Tuple[CheckResult, Union[str, requests.Response]]:
        resp = session.post(
            f'{self.baseurl}/recycle/physical/register',
            data=physical_item,
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'

        if "Serial number is already registered." in resp.text:
            logging.warning('Serial number \'%s\' already used', physical_item["serial"])
            return CheckResult.FAULTY, 'could not store physical item'

        if "/recycle/myitems/physical/" not in resp.url:
            logging.warning('Not redirected to the created item, instead: %s', resp.url)
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'incorrect page after physical item registration'

        item_id = self.get_item_id_for_physical_item_link(resp.url)
        if item_id is None:
            logging.warning("Could not read item id from url: %s", resp.url)
            return CheckResult.FAULTY, 'cannot parse item id'

        if item_id > MAX_ITEM_ID:
            logging.warning("Item Id is too long: %s (Maximum = %s)", item_id, MAX_ITEM_ID)
            return CheckResult.FAULTY, 'wrong item id'

        return CheckResult.OK, resp

    def register_digital_item_while_logged_in(
            self,
            digital_item: Dict,
            session: requests.Session
    ) -> Tuple[CheckResult, Union[str, requests.Response]]:
        data = {
            "item_description": digital_item["item_description"]
        }
        resp = session.post(
            f'{self.baseurl}/recycle/digital/upload',
            data=data,
            files={"datafile": (digital_item["name"], digital_item["content"], 'multipart/form-data')},
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code after digital item registration'

        if "/recycle/myitems/digital/" not in resp.url:
            logging.warning('Not redirected to the created item, instead: %s', resp.url)
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'incorrect page after digital item registration'

        item_id = self.get_item_id_for_digital_item_link(resp.url)
        if item_id is None:
            logging.warning("Could not read item id from url: %s", resp.url)
            return CheckResult.FAULTY, 'cannot parse item id'

        if item_id > MAX_ITEM_ID:
            logging.warning("Item Id is too long: %s (Maximum = %s)", item_id, MAX_ITEM_ID)
            return CheckResult.FAULTY, 'wrong item id'

        return CheckResult.OK, resp

    def get_physical_item_info(
            self,
            item_id: int,
            session: Optional[requests.Session] = None,
            auth_token: Optional[str] = None
    ) -> Tuple[CheckResult, Union[str, Dict]]:
        if session is not None:
            resp = session.get(
                f'{self.baseurl}/recycle/myitems/physical/{item_id}',
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )
        elif auth_token is not None:
            resp = requests.get(
                f'{self.baseurl}/recycle/myitems/physical/{item_id}?authToken={auth_token}',
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )
        else:
            raise AssertionError("Either session or auth_token must be set!")

        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Login failed')
            return CheckResult.FLAG_NOT_FOUND, 'could not log in'

        info = self.parse_info_of_physical_item_page(resp.text)
        if info[0] != CheckResult.OK:
            return info

        return CheckResult.OK, info[1]

    def get_digital_item_info(
            self,
            item_id: int,
            session: Optional[requests.Session] = None,
            auth_token: Optional[str] = None
    ) -> Tuple[CheckResult, Union[str, Dict]]:
        if session is not None:
            resp = session.get(
                f'{self.baseurl}/recycle/myitems/digital/{item_id}',
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )
        elif auth_token is not None:
            resp = requests.get(
                f'{self.baseurl}/recycle/myitems/digital/{item_id}?authToken={auth_token}',
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )
        else:
            raise AssertionError("Either session or auth_token must be set!")

        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on login'

        if resp.url.endswith("/user/login"):
            logging.warning('Login failed')
            return CheckResult.FLAG_NOT_FOUND, 'could not log in'

        info = self.parse_info_of_digital_item_page(resp.text)
        if info[0] != CheckResult.OK:
            return info

        return CheckResult.OK, info[1]


class FlagStoreVariant(abc.ABC):

    def __init__(self, helper: InteractionHelper) -> None:
        self.baseurl = helper.baseurl
        self.timeout = helper.timeout
        self.helper = helper

    @abstractmethod
    def place_flag(self, tick: int, flag: str) -> Tuple[CheckResult, str]:
        pass

    @abstractmethod
    def check_flag(self, tick):
        pass


class PhysicalItemWithAccountVariant(FlagStoreVariant):

    def place_flag(self, tick: int, flag: str) -> Tuple[CheckResult, str]:
        user = self.helper.create_flag_user_details(flag)
        physical_item = self.helper.create_physical_item()
        physical_item["serial"] = flag
        resp = self.helper.register_physical_item_with_user(user, physical_item)
        if resp[0] != CheckResult.OK:
            return resp

        item_id = self.helper.get_item_id_for_physical_item_link(resp[1].url)

        checkerlib.set_flagid(f"physical_acc-{user['email']}-{item_id}")

        info = self.helper.parse_info_of_physical_item_page(resp[1].text)
        if info[0] != CheckResult.OK:
            return info

        if info[1]["serial"] != flag:
            logging.warning('Flag is not printed on the redirected page')
            return CheckResult.FAULTY, 'flag not reflected'

        return CheckResult.OK, ''

    def check_flag(self, tick) -> Tuple[CheckResult, str]:
        flagid = checkerlib.get_flagid(tick)

        if flagid is None:
            return CheckResult.FLAG_NOT_FOUND, 'flag in previous tick not placed'

        if not flagid.startswith("physical_acc-"):
            raise ValueError("Invalid flag id given to flag checker")

        email = flagid.split("-", 1)[1].rsplit("-", 1)[0]

        flag = checkerlib.get_flag(tick)
        pw = self.helper.get_password_by_flag(flag)

        s = requests.Session()
        resp = self.helper.service_login(s, email, pw)
        if resp[0] != CheckResult.OK:
            return resp

        resp = s.get(
            f'{self.baseurl}/recycle/myitems',
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )
        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s when fetching items overview', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on item overview fetching'

        soup = BeautifulSoup(resp.text, 'html.parser')
        td_list = soup.find_all('td')
        td_flag = None
        for td in td_list:
            if td.get_text().strip() == flag:
                # found flag on the overview page
                td_flag = td
                break

        if not td_flag:
            logging.warning("flag not found on the overview page")
            return CheckResult.FLAG_NOT_FOUND, 'flag not on overview page'

        td_created_at = td_flag.findNext("td")
        if not td_created_at:
            logging.warning("physical item table structure invalid (missing created at column)")
            return CheckResult.FAULTY, 'physical item table structure invalid'
        td_status = td_created_at.findNext("td")
        if not td_created_at:
            logging.warning("physical item table structure invalid (missing status column)")
            return CheckResult.FAULTY, 'physical item table structure invalid'
        td_link = td_status.findNext("td")
        if not td_created_at:
            logging.warning("physical item table structure invalid (missing link column)")
            return CheckResult.FAULTY, 'physical item table structure invalid'

        link = td_link.find('a')
        if not link:
            logging.warning("physical item table structure invalid (missing link)")
            return CheckResult.FAULTY, 'physical item table structure invalid'

        link_target = link["href"]
        if not link_target:
            logging.warning("physical item table structure invalid (missing link target)")
            return CheckResult.FAULTY, 'physical item table structure invalid'

        logging.debug('Found physical item link: %s', link_target)

        item_id = self.helper.get_item_id_for_physical_item_link(link_target)
        if item_id is None:
            logging.warning("physical item link invalid: %s", link_target)
            return CheckResult.FAULTY, 'physical item link invalid'

        logging.info("Stored as physical item %s", item_id)

        resp = s.get(
            f"{self.baseurl}/recycle/myitems/physical/{item_id}",
            timeout=self.timeout,
            headers={'User-Agent': get_random_useragent()}
        )

        if resp.status_code == 404:
            logging.warning('Item %s does not exist', item_id)
            return CheckResult.FLAG_NOT_FOUND, 'item not found'

        if resp.status_code != 200:
            logging.warning('Got incorrect status code %s when fetching item', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code on item fetching'

        soup = BeautifulSoup(resp.text, 'html.parser')
        flag_container = soup.find("dd", class_="serial")
        if not flag_container:
            logging.warning('Did not find title element on physical item page')
            return CheckResult.FAULTY, 'incorrect structure on physical item page'

        if flag_container.get_text().strip() != flag:
            logging.warning('Invalid flag on physical item page')
            return CheckResult.FLAG_NOT_FOUND, 'incorrect flag'

        return CheckResult.OK, ''


class PhysicalItemWithoutAccountVariant(FlagStoreVariant):

    def place_flag(self, tick: int, flag: str) -> Tuple[CheckResult, str]:
        physical_item = self.helper.create_physical_item()
        physical_item["serial"] = flag
        resp = self.helper.register_physical_item_anonymous(physical_item)
        if resp[0] != CheckResult.OK:
            return resp

        resp = self.helper.parse_success_box_link(resp[1].text)
        if resp[0] != CheckResult.OK:
            return resp

        item_id, auth_token = resp[1]
        logging.info("Item %s got access token %s", item_id, auth_token)

        checkerlib.set_flagid(f"physical_noacc-{item_id}")

        # store information so the checker can get to the item again
        checkerlib.store_state(f"item_id_{tick}", item_id)
        checkerlib.store_state(f"auth_token_{tick}", auth_token)

        # check for successful item placement
        resp = self.helper.service_get_serial_of_physical_item_with_token(item_id, auth_token)
        if resp[0] != CheckResult.OK:
            return resp

        if resp[1] != flag:
            logging.warning(
                "Flag was not stored on the server correctly (could not be read back). Got '%s' instead",
                resp[1]
            )
            return CheckResult.FAULTY, 'flag not stored correctly'

        return CheckResult.OK, ''

    def check_flag(self, tick) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        item_id = checkerlib.load_state(f"item_id_{tick}")
        auth_token = checkerlib.load_state(f"auth_token_{tick}")

        if flag is None or item_id is None or auth_token is None:
            return CheckResult.FLAG_NOT_FOUND, 'flag in previous tick not placed'

        logging.info("Checking flag for physical item %s with token %s", repr(item_id), repr(auth_token))

        stored_flag = self.helper.service_get_serial_of_physical_item_with_token(item_id, auth_token)
        if stored_flag[0] != CheckResult.OK:
            return stored_flag

        if stored_flag[1] != flag:
            logging.warning("Invalid flag stored under the token: %s", stored_flag[1])
            return CheckResult.FLAG_NOT_FOUND, "invalid flag"

        return CheckResult.OK, ''


class DigitalItemWithAccountVariant(FlagStoreVariant):

    def __init__(self, helper: InteractionHelper, file_gen: FileGenerator) -> None:
        super().__init__(helper)
        self.file_gen = file_gen

    def place_flag(self, tick: int, flag: str) -> Tuple[CheckResult, str]:
        user = self.helper.create_flag_user_details(flag)
        digital_item = self.helper.create_digital_item(self.file_gen, flag, user)
        s = requests.Session()
        resp = self.helper.register_digital_item_with_user(user, digital_item, s)
        if resp[0] != CheckResult.OK:
            return resp

        resp = resp[1]
        item_id = self.helper.get_item_id_for_digital_item_link(resp.url)

        # set the flagid as soon as the flag has been placed
        checkerlib.set_flagid(f"digital_acc-{user['email']}-{item_id}")

        if item_id is None:
            logging.warning('Not redirected to the created item, instead: %s', resp.url)
            logging.info("Failure-Response: %s", resp.text)
            return CheckResult.FAULTY, 'incorrect page'

        checkerlib.store_state(f"item_id_{tick}", item_id)
        checkerlib.store_state(f"file_hash_{tick}", digital_item["hash"])

        logging.info("Uploaded digital item %s with hash: %s", item_id, digital_item["hash"])

        resp = self.helper.download_digital_item_with_session(item_id, s)
        if resp[0] != CheckResult.OK:
            return resp

        stored_hash = sha256(resp[1])

        if digital_item["hash"] != stored_hash:
            logging.warning('Downloaded file has not the same hash as the uploaded one')
            return CheckResult.FAULTY, 'downloaded file incorrect'

        return CheckResult.OK, ''

    def check_flag(self, tick) -> Tuple[CheckResult, str]:
        flagid = checkerlib.get_flagid(tick)

        if flagid is None:
            return CheckResult.FLAG_NOT_FOUND, 'flag in previous tick not placed'

        if not flagid.startswith("digital_acc-"):
            raise ValueError("Invalid flag id given to flag checker")

        email = flagid.split("-", 1)[1].rsplit("-", 1)[0]

        flag = checkerlib.get_flag(tick)
        pw = self.helper.get_password_by_flag(flag)

        s = requests.Session()
        resp = self.helper.service_login(s, email, pw)
        if resp[0] != CheckResult.OK:
            return resp

        item_id = checkerlib.load_state(f"item_id_{tick}")
        file_hash = checkerlib.load_state(f"file_hash_{tick}")

        logging.info("Checking uploaded digital item %s with hash: %s", item_id, file_hash)

        resp = self.helper.download_digital_item_with_session(item_id, s)
        if resp[0] != CheckResult.OK:
            return resp

        stored_hash = sha256(resp[1])
        if file_hash != stored_hash:
            logging.warning("File hash mismatches from expected")
            return CheckResult.FLAG_NOT_FOUND, 'incorrect file downloaded'

        return CheckResult.OK, ''


class DigitalItemWithoutAccountVariant(FlagStoreVariant):

    def __init__(self, helper: InteractionHelper, file_gen: FileGenerator) -> None:
        super().__init__(helper)
        self.file_gen = file_gen

    def place_flag(self, tick: int, flag: str) -> Tuple[CheckResult, str]:
        digital_item = self.helper.create_digital_item(self.file_gen, flag)
        s = requests.Session()
        resp = self.helper.register_digital_item_anonymous(digital_item, s)
        if resp[0] != CheckResult.OK:
            return resp

        resp = self.helper.parse_success_box_link(resp[1].text)
        if resp[0] != CheckResult.OK:
            return resp

        item_id, auth_token = resp[1]
        logging.info("Item %s got access token %s", item_id, auth_token)

        checkerlib.set_flagid(f"digital_noacc-{item_id}")

        # store information so the checker can get to the item again
        checkerlib.store_state(f"item_id_{tick}", item_id)
        checkerlib.store_state(f"auth_token_{tick}", auth_token)
        checkerlib.store_state(f"file_hash_{tick}", digital_item["hash"])

        # check for successful item placement
        resp = self.helper.download_digital_item_with_token(item_id, auth_token)
        if resp[0] != CheckResult.OK:
            return resp

        stored_hash = sha256(resp[1])

        if stored_hash != digital_item["hash"]:
            logging.warning("Flag was not stored on the server correctly (could not be read back). Hash mismatch.")
            return CheckResult.FAULTY, 'flag not stored correctly'

        return CheckResult.OK, ''

    def check_flag(self, tick) -> Tuple[CheckResult, str]:
        item_id = checkerlib.load_state(f"item_id_{tick}")
        auth_token = checkerlib.load_state(f"auth_token_{tick}")
        file_hash = checkerlib.load_state(f"file_hash_{tick}")

        if item_id is None or auth_token is None or file_hash is None:
            return CheckResult.FLAG_NOT_FOUND, 'flag in previous tick not placed'

        logging.info("Checking hash for digital item %s with token %s", repr(item_id), repr(auth_token))

        stored_file = self.helper.download_digital_item_with_token(item_id, auth_token)
        if stored_file[0] != CheckResult.OK:
            return stored_file

        stored_hash = sha256(stored_file[1])

        if file_hash != stored_hash:
            logging.warning("Invalid file stored under the token: %s", stored_file[1])
            return CheckResult.FLAG_NOT_FOUND, "invalid flag"

        return CheckResult.OK, ''


class DewasteChecker1(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10010
        self.timeout = 5  # don't forget to set a timeout for every request you send
        self.flagsecret = FLAG_SECRET
        self.baseurl = f'http://{self.ip}:{self.port}'
        self.helper = InteractionHelper(self.baseurl, self.timeout)
        self.processing_max_wait_iterations = 7
        self.processing_wait_time = 2

    def get_flag_options(self):
        def opt(name: str, variant: FlagStoreVariant) -> Dict:
            return {"name": name, "place_flag": variant.place_flag, "check_flag": variant.check_flag}

        # File gen is not needed for checking the flag -> does not matter if it is different for checking flags
        file_gen = random.choice(self.get_available_file_generators())

        return [
            opt("physical_item", PhysicalItemWithAccountVariant(self.helper)),
            opt("physical_item_anonymous", PhysicalItemWithoutAccountVariant(self.helper)),
            opt("digital_item", DigitalItemWithAccountVariant(self.helper, file_gen)),
            opt("digital_item_anonymous", DigitalItemWithoutAccountVariant(self.helper, file_gen))
        ]

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        flag_options = self.get_flag_options()
        selected_option = flag_options[tick % len(flag_options)]

        logging.info("Storing flag of type %s for tick %s", selected_option['name'], tick)
        return selected_option["place_flag"](tick, flag)

    def check_service(self) -> Tuple[CheckResult, str]:
        checker_methods = [
            self.check_ranking_functionality,
            self.check_faq_functionality,
            self.check_basic_item_functionality,
            self.check_digital_item_processing_functionality,
        ]
        random.shuffle(checker_methods)

        for m in checker_methods:
            resp = m()
            if resp[0] != CheckResult.OK:
                if resp[0] == CheckResult.FLAG_NOT_FOUND:
                    resp = (CheckResult.FAULTY, resp[1])
                return resp

        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag_options = self.get_flag_options()
        selected_option = flag_options[tick % len(flag_options)]

        logging.info("Checking flag of type %s for tick %s", selected_option['name'], tick)
        return selected_option["check_flag"](tick)

    def check_ranking_functionality(self) -> Tuple[CheckResult, str]:
        def check_ranking_ids(ranking) -> Tuple[CheckResult, str]:
            id_set = {*map(lambda e: e["user_id"], ranking)}
            if len(ranking) != len(id_set):
                logging.info("Something wrong with the ids on the ranking page")
                return CheckResult.FAULTY, 'invalid ranking'
            return CheckResult.OK, ''

        # check if ranking page is correct
        if random.randint(0, 3) == 0:
            resp = self.helper.get_ranking()
            if resp[0] != CheckResult.OK:
                return resp

            resp = check_ranking_ids(resp[1])
            if resp[0] != CheckResult.OK:
                return resp

        user = self.helper.create_flag_user_details(random_chars(random.randint(10, 30)))
        physical_item = self.helper.create_physical_item()

        # add a user and check if it is in the ranking
        s = requests.Session()
        resp = self.helper.register_physical_item_with_user(user, physical_item, s)
        if resp[0] != CheckResult.OK:
            return resp

        resp = self.helper.get_ranking(s if random.randint(0, 1) == 0 else None)
        if resp[0] != CheckResult.OK:
            return resp

        ranking = resp[1]
        resp = check_ranking_ids(ranking)
        if resp[0] != CheckResult.OK:
            return resp

        for ranking_entry in ranking:
            if ranking_entry["email"] == user["email"]:
                if ranking_entry["fullname"] == user["firstname"] + " " + user["lastname"]:
                    logging.info("Found the user that was just created on the scoreboard")
                    logging.info("Ranking functionality correct")
                    return CheckResult.OK, ''

        logging.warning("A user that was just created is not visible on the ranking page.")
        return CheckResult.FAULTY, 'incorrect scoreboard'

    def check_faq_functionality(self) -> Tuple[CheckResult, str]:
        expected_faq_entries = self.get_expected_faq_entries()

        results = self.helper.get_faq()
        if results[0] != CheckResult.OK:
            return results
        if len(results[1]) < len(expected_faq_entries):
            logging.warning("Missing faq results")
            return CheckResult.FAULTY, 'missing faq results'

        # take one expected faq, build a query for it and check if it is in the result
        expected = random.choice(expected_faq_entries)
        clean_content = lambda content: re.sub(r'[^a-zA-Z0-9+",\.\(\) \-]', '', content)
        cleaned_searchable_content = clean_content(expected["question"] + " " + expected["answer"])
        query = " ".join(random.choices(cleaned_searchable_content.split(" "), k=random.randint(2, 6)))
        results = self.helper.get_faq(query)
        if results[0] != CheckResult.OK:
            return results

        def fuzzy_compare(c1, c2) -> bool:
            c1 = re.sub(r'[^a-zA-Z0-9]', '', c1)
            c2 = re.sub(r'[^a-zA-Z0-9]', '', c2)
            return c1 == c2

        for result in results[1]:
            if fuzzy_compare(result["question"], expected["question"]) and fuzzy_compare(result["answer"], expected["answer"]):
                logging.info("FAQ functionality OK")
                return CheckResult.OK, ''

        logging.warning("Service did not respond with the correct faq answer to the query: %s", query)
        logging.info("Expected: %s", expected)
        logging.info("Got: %s", results[1])
        return CheckResult.FAULTY, 'missing faq entry'

    def get_expected_faq_entries(self) -> List[Dict]:
        def e(q: str, a: str) -> Dict:
            return {"question": q, "answer": a}

        return [
            e(
                'How do you recycle e-waste?',
                'Our plant is fully powered by a team of robots called W.I.E.N. short for Waste Inspector Electronic Navigators Created from recycled waste, they are doing their job with the expected professionalism. They are programmed to scan your items in less than a minute and determine the exact compound. The items are then sent to the department of reconstruction. Other robots dismount the goods and send the ingredients to other departments depending on the recovered materials.'
            ),
            e(
                'What about digital waste?',
                'Digital waste, such as compressed archives, will be processed by the Deep hOlistic Neuro-Data EntanglEment Scalable Tensor Array unit (internally referenced by our employees as DONDEESTA for the sake of brevity). The purpose of DONDEESTA is to subsume the knowledge extrapolated from all uploaded files and restructure it to be easily accessible. Unfortunately, given the extremely complicated architecture of the system, digital waste is only stored at the moment without being further processed. We will inform you whenever DONDEESTA becomes operational.'
            ),
            e(
                'How much digital data can I upload at once?',
                'Please refer to the limits specified in the recycle page.'
            ),
            e(
                'How is my contribution valuable to our community?',
                'With all the knowledge we receive from digital waste, we plan to create an open system where people will be able to find all the information collected by our ancestors. It can help us rebuild society way faster than currently expected and avoid the mistakes previously made by humanity. Concerning recycling of e-waste, we plan to produce new devices by fully recycling electronic junk. This is not simply advisable but comes out of necessity since natural resources on the planet have been fully exploited by previous generations.'
            ),
            e(
                'Who is running the waste recycling company?',
                'Two persons who care about their community. You can read more in the about page.'
            ),
            e(
                'How can I help even further?',
                'Robots and drones mostly operate the plant. However, we always need talented people to develop more efficient algorithms and fix some seldom major breakage (the robots themselves can fix minor issues). You can also file a bug report if you find a vulnerability that affects the Web interface.'
            )
        ]

    def get_available_file_generators(self) -> List[FileGenerator]:
        inner_generators = [
            TextFileGenerator(),
            ImageFileGenerator()
        ]

        ret = []
        for compression in [None, "", "gz", "bz2"]:
            for inner in inner_generators:
                if compression is None:
                    ret += [inner]
                else:
                    ret += [TarFileGenerator(inner, compression)]
        return ret

    def check_basic_item_functionality(self) -> Tuple[CheckResult, str]:
        user = self.helper.create_flag_user_details(random_chars(random.randint(10, 30)))
        s = requests.Session()

        is_first_item_physical = random.randint(0, 1) == 0
        if is_first_item_physical:
            physical_item = self.helper.create_physical_item()
            resp = self.helper.register_physical_item_with_user(user, physical_item, s)
            if resp[0] != CheckResult.OK:
                return resp
            item_id = self.helper.get_item_id_for_physical_item_link(resp[1].url)
        else:
            file_gen = random.choice(self.get_available_file_generators())
            digital_item = self.helper.create_digital_item(file_gen, user=user)
            resp = self.helper.register_digital_item_with_user(user, digital_item, s)
            if resp[0] != CheckResult.OK:
                return resp
            item_id = self.helper.get_item_id_for_digital_item_link(resp[1].url)

        resp = self.helper.service_logout(s)
        if resp[0] != CheckResult.OK:
            return resp

        if is_first_item_physical:
            resp = s.get(
                f"{self.baseurl}/recycle/myitems/physical/{item_id}",
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )
        else:
            resp = s.get(
                f"{self.baseurl}/recycle/myitems/digital/{item_id}",
                timeout=self.timeout,
                headers={'User-Agent': get_random_useragent()}
            )

        if not resp.url.endswith("/user/login"):
            logging.warning("Something is wrong. I have just logged out and still can access my item.")
            return CheckResult.FAULTY, "open door"

        s = requests.Session()
        self.helper.service_login(s, user["email"], user["password"])

        if random.randint(0, 2) > 0:
            physical_item = self.helper.create_physical_item()
            resp = self.helper.register_physical_item_while_logged_in(physical_item, s)
            if resp[0] != CheckResult.OK:
                return resp
            item_id = self.helper.get_item_id_for_physical_item_link(resp[1].url)
            physical_item_returned = self.helper.get_physical_item_info(item_id, session=s)
            if physical_item_returned[0] != CheckResult.OK:
                return physical_item_returned
            physical_item_returned = physical_item_returned[1]

            to_check = {
                'serial': 'Serial number',
                'item_description': "Item description",
                'length': "Length",
                'width': 'Width',
                'height': 'Height',
                "weight": "Weight"
            }

            for k, v in to_check.items():
                if physical_item[k] != physical_item_returned[k]:
                    logging.warning(
                        "%s of stored item mismatches: '%s' != '%s'",
                        v,
                        physical_item[k],
                        physical_item_returned[k]
                    )
                    return CheckResult.FAULTY, 'physical item not correct'

        if random.randint(0, 2) > 0:
            file_gen = random.choice(self.get_available_file_generators())
            digital_item = self.helper.create_digital_item(file_gen)
            resp = self.helper.register_digital_item_while_logged_in(digital_item, s)
            if resp[0] != CheckResult.OK:
                return resp
            item_id = self.helper.get_item_id_for_digital_item_link(resp[1].url)
            digital_item_returned = self.helper.get_digital_item_info(item_id, session=s)
            if digital_item_returned[0] != CheckResult.OK:
                return digital_item_returned
            digital_item_returned = digital_item_returned[1]

            to_check = {
                'item_description': "Item description",
            }

            for k, v in to_check.items():
                if digital_item[k] != digital_item_returned[k]:
                    logging.warning(
                        "%s of stored item mismatches: '%s' != '%s'",
                        v,
                        digital_item[k],
                        digital_item_returned[k]
                    )
                    return CheckResult.FAULTY, 'digital item not correct'

            downloaded = self.helper.download_digital_item_with_session(item_id, s)
            if downloaded[0] != CheckResult.OK:
                return downloaded

            downloaded_hash = sha256(downloaded[1])

            if digital_item["hash"] != downloaded_hash:
                logging.warning("Downloaded file has a different hash, than the uploaded one")
                return CheckResult.FAULTY, "invalid file downloaded"

        logging.info("Basic item functionality OK")
        return CheckResult.OK, ''

    def create_processing_ini_test_file(self, with_account: bool):
        sections = []
        for i in range(random.randint(1, 5)):
            name = random_chars(1, string.ascii_letters) + random_chars(random.randint(2, 10))
            fields = {}
            for j in range(random.randint(1, 5)):
                key = random_chars(random.randint(1, 10))
                if key.lower() in ["null", "yes", "no", "true", "false", "on", "off", "none"]:
                    # These are reserved names, that are not allowed as keys...
                    key += random_chars(1)
                value = random_chars(random.randint(1, 10))
                if value.lower() in ["null", "yes", "no", "true", "false", "on", "off", "none"]:
                    # PHP will treat these values differently, so our "expected" logic does not work in this case
                    value += random_chars(1)
                fields[key] = value
            sections.append({"name": name, "fields": fields})

        content = ""
        expected = ""
        for section in sections:
            content += f"[{section['name']}]\n"
            expected += f"[{section['name']}]\n"
            for key, value in section['fields'].items():
                space1 = " " * random.randint(0, 1)
                space2 = " " * random.randint(0, 1)
                content += f"{key}{space1}={space2}{value}\n"
                expected += f"{key} = {value}\n"

        file_gen = StaticFileGenerator(content.encode('latin-1'), "ini")

        def checker(results: List[Dict]) -> bool:
            ini_results = list(filter(lambda r: r["type"] == "ini", results))
            num_ini_results = len(ini_results)
            if num_ini_results != 1:
                logging.warning("Expected a single ini result, but got %s", num_ini_results)
                return False

            result_content = ini_results[0]["content"].strip()
            if result_content != expected.strip():
                logging.warning("Unexpected ini result. Expected '%s', Got: '%s'", expected.strip(), result_content)
                return False

            if with_account:
                file_results = list(filter(lambda r: r["type"] == "file", results))
                num_file_results = len(file_results)
                if num_file_results != 1:
                    logging.warning("Expected a single file result, but got %s", num_file_results)
                    return False

                result_content = file_results[0]["content"].strip()
                if "ASCII text" not in result_content and "JSON data" not in result_content:
                    logging.warning("Invalid file result. Expected 'ASCII text', but got: '%s'", result_content)
                    return False

            return True

        return file_gen, checker

    def create_processing_eml_test_file(self, with_account: bool) -> Tuple[FileGenerator, Callable]:
        firstname = self.helper.fake.first_name()
        lastname = self.helper.fake.last_name()
        email = firstname.lower() + "@" + lastname.lower() + ".invalid"

        firstname2 = self.helper.fake.first_name()
        lastname2 = self.helper.fake.last_name()
        email2 = firstname2.lower() + "@" + lastname2.lower() + ".invalid"

        import email.utils as emailX

        headers = [
            ("Return-Path", email),
            ("To", email2),
            ("From", email),
            ("Reply-To", email),
            ("Date", emailX.format_datetime(self.helper.fake.date_time_between()))
        ]

        random.shuffle(headers)

        content = "\r\n".join(map(lambda x: x[0] + ": " + x[1], headers))
        content += "\r\n" * 2
        content += self.helper.fake.text() + "\r\n\r\n"

        file_gen = StaticFileGenerator(content.encode('latin-1'), "eml")

        def checker(results: List[Dict]) -> bool:
            # not checking EML parser as it is buggy anyway and does not provide sensible output
            if with_account:
                file_results = list(filter(lambda r: r["type"] == "file", results))
                num_file_results = len(file_results)
                if num_file_results != 1:
                    logging.warning("Expected a single file result, but got %s", num_file_results)
                    return False

                result_content = file_results[0]["content"].strip()
                if "ASCII text" not in result_content:
                    logging.warning("Invalid file result. Expected 'ASCII text', but got: '%s'", result_content)
                    return False

            return True

        return file_gen, checker

    def create_processing_test_file(self, with_account: bool) -> Tuple[FileGenerator, Callable]:
        options = [
            self.create_processing_ini_test_file,
            self.create_processing_eml_test_file
        ]
        return random.choice(options)(with_account)

    def check_digital_item_processing_functionality(self) -> Tuple[CheckResult, str]:
        with_account = random.randint(0, 1) == 0

        file_gen, file_checker = self.create_processing_test_file(with_account)

        ret_info = None
        s = None
        auth_token = None

        # upload as either user or anon
        if with_account:
            user = self.helper.create_flag_user_details(random_chars(random.randint(10, 30)))
            s = requests.Session()
            digital_item = self.helper.create_digital_item(file_gen, user=user)
            resp = self.helper.register_digital_item_with_user(user, digital_item, s)
            if resp[0] != CheckResult.OK:
                return resp
            item_id = self.helper.get_item_id_for_digital_item_link(resp[1].url)
            logging.info("Item %s uploaded for user %s with password %s", item_id, user["email"], user["password"])
        else:
            digital_item = self.helper.create_digital_item(file_gen)
            resp = self.helper.register_digital_item_anonymous(digital_item)
            if resp[0] != CheckResult.OK:
                return resp
            resp = self.helper.parse_success_box_link(resp[1].text)
            if resp[0] != CheckResult.OK:
                return resp

            item_id, auth_token = resp[1]
            logging.info("Item %s uploaded for and got auth_token '%s'", item_id, auth_token)

        # wait for item being processed
        i = 0
        while i < self.processing_max_wait_iterations:
            info = self.helper.get_digital_item_info(item_id, session=s, auth_token=auth_token)
            if info[0] != CheckResult.OK:
                return info
            if info[1]["status"] == "processed":
                ret_info = info[1]
                break
            logging.info(
                "Waiting for item being processed (iteration = %s, max_iteration = %s, wait_time = %s)",
                i,
                self.processing_max_wait_iterations,
                self.processing_wait_time
            )
            time.sleep(self.processing_wait_time)
            i += 1

        if ret_info is None:
            logging.warning("Service did not process item in time")
            return CheckResult.FAULTY, 'item not processed in time'

        # check output
        if not file_checker(ret_info["results"]):
            logging.warning("Service did not process item correctly. Expected different results")
            return CheckResult.FAULTY, 'item not processed correctly'

        logging.info("Digital item processing OK")
        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(DewasteChecker1)
