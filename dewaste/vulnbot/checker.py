#!/usr/bin/env python3

import io
import abc
import json
import time
import base64
import string
import random
import tarfile
import logging
import requests
from abc import abstractmethod
from typing import Tuple, List
from threading import Timer
from http.cookies import SimpleCookie
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


FILE_TMP_DIR = '/tmp'
CHROME_IMPLICIT_TIMEOUT = 15
CHROME_PAGE_TIMEOUT = 7
EXPLOIT_TIMEOUT = 3 # seconds for the exploit to run
REQUEST_TIMEOUT = 3 # this is for python requests, we use requests instead of a browser when possible
FLAG_COUNT = 5 # number of flags to keep in the browser
REPORT_APP_PORT = 11111
COOKIE_NAME = '_unpacked_dict-v1'


class FileGenerator(abc.ABC):
    @abstractmethod
    def generate(self, flag: str) -> Tuple[bytes, str]:
        """Generates a new file with the flag somewhere inside. Returns the content and the file extension."""
        pass


class StaticFileGenerator(FileGenerator):
    exts = ['out', 'log', 'data', 'diff', 'foo', 'bar']

    def generate(self, flag: str) -> Tuple[bytes, str]:
        content = flag.encode('latin-1')
        file_ext = random.choice(self.exts)
        return content, file_ext


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
        font_height = 11 #manually measured at font-size 14
        txt = flag
        file_ext = random.choice(self.exts)
        img_width, img_height = [random.randint(330, 350), random.randint(20, 40)]
        # stick to dejavu mono as a font
        fnt = ImageFont.truetype('dejavu.ttf', 14)
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

    def __init__(self, file_gens: List[FileGenerator], compression: str = "") -> None:
        super().__init__()
        self.file_gens = file_gens
        self.file_contents = dict() # key is the pathname, value is the content

        valid_modes = ["", "gz", "bz2"]
        if compression not in valid_modes:
            raise ValueError(f"Invalid compression mode '{compression}'. Valid: " + ", ".join(valid_modes))
        self._compression = compression

    def generate(self, flag: str) -> Tuple[bytes, str]:
        fh = io.BytesIO()
        with tarfile.open(fileobj=fh, mode='w:' + self._compression) as tar:
            for file_gen in self.file_gens:
                flag_file, flag_ext = file_gen.generate(flag)

                path = ""
                for i in range(random.randint(0, 5)):
                    path += random_chars(random.randint(5, 10)) + "/"
                file_path = path + random_chars(random.randint(5, 10)) + '.' + flag_ext
                info = tarfile.TarInfo(file_path)
                info.size = len(flag_file)
                tar.addfile(info, io.BytesIO(flag_file))

                self.file_contents[file_path] = flag_file
        return fh.getvalue(), "tar." + self._compression if self._compression != "" else "tar"


class DewasteChecker2(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int, checkerlib=checkerlib):
        super().__init__(ip, team)
        self.checkerlib = checkerlib
        self.ip = ip
        self.port = 10010
        self.timeout = 10  # don't forget to set a timeout for every request you send
        self.baseurl = f'http://{self.ip}:{self.port}'
        self.reporturl = f'http://{self.ip}:{REPORT_APP_PORT}' 
        self.driver = None
        self.flags = []
        self.requests_session = None # we want to reuse it later, this is promoted to authenticated
        self.files_dict = None # {file_path: b64(file_content)}
        self.cookie_dict = None # {name: COOKIE_NAME, vaue: json.dumps(file_listing)}


    def _create_driver(self):
        options = selenium.webdriver.ChromeOptions()
        # always enable headless in production
        options.add_argument("--headless") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--password-store=basic")
        options.add_argument("--no-gpu")
        options.add_argument("--window-size=1024x768")

        # straight from stackoverflow, https://stackoverflow.com/a/66993941
        options.add_experimental_option('prefs', {
            'download.default_directory': FILE_TMP_DIR,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing_for_trusted_sources_enabled': False,
            'safebrowsing.enabled': False
        })

        self.driver = selenium.webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(CHROME_PAGE_TIMEOUT)


    def _quit(self):
        '''
        Just quit the browser.
        '''
        self.driver.quit()


    def _get_flags(self, tick):
        '''
        Store into self.flags last FLAG_COUNT flags.
        '''

        for t in range(max(tick-FLAG_COUNT+1, 0), tick+1):
            self.flags.append(self.checkerlib.get_flag(t))


    def _authenticate(self):
        '''
        Authenticate and build self.requests_session so we can resue it later. Return URLs.
        '''
        
        # load private key to solve the challenge-response protocol
        with open('./private_key.pem', 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
        
        self.requests_session = requests.Session()

        # obtain the challenge
        challenge = base64.b64decode(
            self.requests_session.get(
                f'{self.reporturl}/admin/challenge',
                timeout=REQUEST_TIMEOUT
            ).json()['challenge']
        )

        # sign the challenge
        signature = private_key.sign(
            challenge,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        # get the list of URLs to visit
        urls = self.requests_session.post(
            f'{self.reporturl}/admin/list',
            data={'signature': base64.b64encode(signature)},
            timeout=REQUEST_TIMEOUT
        ).json()

        return urls

    def _get_urls(self):
        '''
        Return all the URLs that should be visited.
        '''
        urls = self.requests_session.post(
            f'{self.reporturl}/admin/list',
            timeout=REQUEST_TIMEOUT
        ).json()

        return urls

    def _prepare_files(self):
        # get N generators, last one is always ImageGenerator
        generators = [random.choice([StaticFileGenerator, TextFileGenerator]) for _ in range(len(self.flags))]
        generators[-1] = ImageFileGenerator
        files_dict = dict()
        for flag, generator in zip(self.flags, generators):
            f_content, ext = generator().generate(flag)
            path = ""
            for i in range(random.randint(0, 5)):
                path += random_chars(random.randint(5, 10)) + "/"

            f_path = f'./{path}{random_chars(len=random.randint(5, 20))}.{ext}'
            files_dict[f_path] = base64.b64encode(f_content).decode()
        cookie_value = {f_path: "0o100664" for f_path in files_dict.keys()}
        self.files_dict = files_dict
        cookie = SimpleCookie()
        cookie[COOKIE_NAME] = json.dumps(cookie_value)
        self.cookie = cookie


    def _get_script_to_execute(self):
        # this stuff is horrible and literally makes no sense, but it reflects what the pyscript
        # code does so...
        cookie_out = self.cookie[COOKIE_NAME].OutputString().replace('"', '\\"')
        script = f"document.cookie = '{cookie_out}';\n"
        for pathname, data in self.files_dict.items():
            script += f'localStorage.setItem("{pathname}", "{data}");\n'
        return script

    def _visit(self, url):
        '''
        Mark the URL as visited, try to visit it and them report it.
        '''

        logging.info(f'Visiting URL: {url["uuid"]}')
        
        # mark the URL as visited first
        self.requests_session.post(
            f'{self.reporturl}/admin/{url["uuid"]}',
            timeout=REQUEST_TIMEOUT     
        )

        # check if this is a valid url
        if not url['url'].startswith(self.baseurl):
            logging.warning(f'Invalid URL: {url["uuid"]}')
            # send a message saying that the URL is invalid. No need to attach the session cookie
            requests.post(
                f'{self.reporturl}/report/{url["uuid"]}',
                data={'message': f'Invalid URL, should start with {self.baseurl}.'},
                timeout=REQUEST_TIMEOUT     
            )
            return False

        # let's start the browser now
        try:
            self._create_driver()
            # start a watchdog to kill Chrome if needed, e.g., if a while(true) is executed
            timer = Timer(
                CHROME_IMPLICIT_TIMEOUT + EXPLOIT_TIMEOUT + 2,
                watchdog_task,
                args=(self.driver,))
            timer.start()
            # load a page in the origin of the expplication
            self.driver.get(self.baseurl)
            # create the state with flags
            self.driver.execute_script(self._get_script_to_execute())
            # visit the malicious URL
            self.driver.get(url['url'])
            # wait for pyscript to run
            WebDriverWait(self.driver, CHROME_IMPLICIT_TIMEOUT).until_not(
                EC.presence_of_element_located((By.TAG_NAME, 'py-loader'))
            )
            # wait additional EXPLOIT_TIMEOUT for the explpoit to run
            time.sleep(EXPLOIT_TIMEOUT)
        except Exception as e:
            logging.error(f'Exception while visiting {url["uuid"]}: {e}')
        
        # quit the driver (this call gets stuck without the watchdog)
        self._quit()
        # cancel the timer
        timer.cancel()

        # send a message saying that we processed the request, no need to attach the session cookie
        requests.post(
            f'{self.reporturl}/report/{url["uuid"]}',
            data={'message': 'Thank you, we finished processing your request.'},
            timeout=REQUEST_TIMEOUT     
        )


    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        self._get_flags(tick)
        logging.info(f'Got flags: {self.flags}')
        urls = self._authenticate()

        # quit if there are no URLs to visit
        if not urls:
            logging.info('No URLs found, aborting')
            return CheckResult.OK, ''

        # generate datastructures to be injected in the browser to populate it with flags
        self._prepare_files()
        
        # to minimize interferences between parallel bots, we request every single time the list of
        # URLs to visit. Then we pick the 10th most recent one (or the oldest one if the queue is
        # <10). This should ensure that links are visited reasonably quickly, still exhausting the
        # queue of provided links
        while True:
            urls = self._get_urls()
            if not urls:
                break
            # take the newest 10 links
            urls = urls[-10:]
            # and get the oldest one among these
            url = urls[0]
            try:
                self._visit(url)
            except Exception as e:
                logging.error(f'Exception while visiting {url.items()}: {e}')
        
        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        return CheckResult.OK, ''


# utility functions

def random_chars(len: int, charset: str = string.ascii_letters + string.digits + '_') -> str:
    return ''.join(random.choices(charset, k=len))

def watchdog_task(driver):
    import os, signal
    
    logging.critical('Watchdog triggered, killing Chrome')
    # among the different ways, this is the most brutal but effective
    os.system('/usr/bin/pkill -9 "chrome"')
    # driver.service.send_remote_shutdown_command()
    # os.kill(driver.service.process.pid, signal.SIGKILL)
    time.sleep(1)



checker_class = DewasteChecker2 # IMPORTANT set to the name of the class!
if __name__ == '__main__':
    checkerlib.run_check(DewasteChecker2)
