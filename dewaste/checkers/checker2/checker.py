#!/usr/bin/env python3

import io
import abc
import time
import string
import random
import tarfile
import logging
import traceback

from abc import abstractmethod
from typing import Tuple, List

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
CHROME_IMPLICIT_TIMEOUT = 20
CHROME_PAGE_LOAD_TIMEOUT = 15
CHROME_SCRIPT_TIMEOUT = 15


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

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10010
        self.timeout = 10  # don't forget to set a timeout for every request you send
        self.baseurl = f'http://{self.ip}:{self.port}'
        self.driver = None
        self.flag = None
        self.tar_generator = None
        self.tar_href = None


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
        self.driver.set_page_load_timeout(CHROME_PAGE_LOAD_TIMEOUT)
        self.driver.set_script_timeout(CHROME_SCRIPT_TIMEOUT)


    def _quit(self):
        '''
        Just quit the browser.
        '''
        self.driver.quit()


    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        # add a random sleep at the beginning
        time.sleep(random.randint(0, 5))

        # create driver
        self._create_driver()
        
        # first connect
        try:
            self.driver.get(f'{self.baseurl}/analyze')
        except Exception as e:
            message = 'Unable to connect'
            logging.warning(f'{message}: {e}')
            self._quit()
            return CheckResult.DOWN, message
        
        # generate a static file and an archive containing the flag
        static_generator = random.choice([StaticFileGenerator, TextFileGenerator, ImageFileGenerator])
        f_name = generator_to_disk(
            random_chars(len=random.randint(5, 35)),
            static_generator()
        )

        self.flag = checkerlib.get_flag(tick)
        self.tar_generator = TarFileGenerator(
            [TextFileGenerator(), ImageFileGenerator()],
            random.choice(["", "gz", "bz2"])
        )
        tar_f_name = generator_to_disk(self.flag, self.tar_generator)

        # use an explicity wait https://selenium-python.readthedocs.io/waits.html#explicit-waits
        # to wait for the runtime to be loaded. Abort if more than TIMEOUT_IMPLICIT seconds pass.
        try:
            WebDriverWait(self.driver, CHROME_IMPLICIT_TIMEOUT).until_not(
                EC.presence_of_element_located((By.TAG_NAME, 'py-loader'))
            )
            time.sleep(2)
            # send files
            elem = self.driver.find_element(By.ID, 'upload')
            elem.send_keys(f'{FILE_TMP_DIR}/{f_name}')
            elem.send_keys(f'{FILE_TMP_DIR}/{tar_f_name}')
            # wait for files to be processed
            WebDriverWait(self.driver, CHROME_IMPLICIT_TIMEOUT).until_not(
                EC.presence_of_element_located((By.TAG_NAME, 'out-1'))
            )
            elem = self.driver.find_element(By.ID, 'out')
            # check that messages are printed correctly
            assert f'[!] {f_name} is not a valid archive file' in elem.text
            assert f'[*] Analyzing {tar_f_name}' in elem.text
        except Exception as e:
            message = 'Problem while uploading files'
            logging.warning(f'{message}: {e}')
            traceback.print_exc()
            self._quit()
            return CheckResult.FAULTY, message

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        # 1. test the download function
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, '#col-download a')
            file_name = elem.get_attribute('download')
            elem.click()
            # sleep 2 second and then access the downloaded file
            time.sleep(2)
            with tarfile.open(f'{FILE_TMP_DIR}/{file_name}', 'r') as f:
                for file_name, file_content in self.tar_generator.file_contents.items():
                    assert file_content == f.extractfile(f'./{file_name}').read()
        except Exception as e:
            message = 'Problem while downloading the archive'
            logging.warning(f'{message}: {e}')
            traceback.print_exc()
            self._quit()
            return CheckResult.FAULTY, message
        
        # 2. test the URL generation function (just click and obtain the URL)
        try:
            elem = self.driver.find_element(By.ID, 'portable')
            elem.click()
            time.sleep(0.5)
            elem = self.driver.find_element(By.CSS_SELECTOR, '#col-portable a')
            self.tar_href = elem.get_attribute('href')
        except Exception as e:
            message = 'Problem while generating the portable URL'
            logging.warning(f'{message}: {e}')
            traceback.print_exc()
            self._quit()
            return CheckResult.FAULTY, message

        # 3. check that the archive uploaded during check_flag() persists a page reload
        try:
            self.driver.get(f'{self.baseurl}/analyze')
            WebDriverWait(self.driver, CHROME_IMPLICIT_TIMEOUT).until_not(
                EC.presence_of_element_located((By.TAG_NAME, 'py-loader'))
            )
            time.sleep(1)
            elem = self.driver.find_element(By.ID, 'tree')
            for file_path in self.tar_generator.file_contents.keys():
                assert f'./{file_path}' in elem.text
            assert self.flag in elem.text
        except Exception as e:
            message = 'Cannot retrieve persistent state after refresh'
            logging.warning(f'{message}: {e}')
            traceback.print_exc()
            self._quit()
            return CheckResult.FAULTY, message

        # 4. test that the URL generated at step 2 can recreate the files in a fresh browser session
        self._quit()
        self._create_driver()
        try:
            self.driver.get(self.tar_href)
            WebDriverWait(self.driver, CHROME_IMPLICIT_TIMEOUT).until_not(
                EC.presence_of_element_located((By.TAG_NAME, 'py-loader'))
            )
            time.sleep(1)
            elem = self.driver.find_element(By.ID, 'tree')
            for file_path in self.tar_generator.file_contents.keys():
                assert f'./{file_path}' in elem.text
            assert self.flag in elem.text
        except Exception as e:
            message = 'Cannot retrieve files after visiting a portable URL'
            logging.warning(f'{message}: {e}')
            traceback.print_exc()
            return CheckResult.FAULTY, message
        finally:
            self._quit()
        
        return CheckResult.OK, ''

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:

        # we check the flag in check_service() as part of the service functionality. There is no
        # reason to re-test N-times the presence of the flag, since there is no concept of 
        # server-side storage

        return CheckResult.OK, ''


# utility functions

def random_chars(len: int, charset: str = string.ascii_letters + string.digits + '_') -> str:
    return ''.join(random.choices(charset, k=len))


def generator_to_disk(content, fg):
    """
    Write a file to FILE_TMP_DIR and return its file name.
    """
    f_content, ext = fg.generate(content)
    f_name = f'{random_chars(len=random.randint(5, 20))}.{ext}'
    with open(f'{FILE_TMP_DIR}/{f_name}', 'wb') as f:
        f.write(f_content)
    return f_name


if __name__ == '__main__':
    checkerlib.run_check(DewasteChecker2)
