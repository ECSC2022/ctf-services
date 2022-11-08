#!/usr/bin/env python3
import logging
import asyncio
import os
import httpx
import random
import secrets
import json
import io

from random import shuffle
from typing import Tuple
from pathlib import Path
from vgm.instruction import VGM

#import requests
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult
from cantinautils import orderflow


class CantinaChecker2(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.gw_port = 10020
        self.pos_port = 10021
        self.juk_port = 10024
        self.timeout = 5 
        self.flagsecret = "2efada9e312fb6e690aad724eaeaf6ba83de"
        self.baseurl_ticket = f"http://{self.ip}:{self.pos_port}"
        self.baseurl_juke = f"http://{self.ip}:{self.juk_port}"
        

        self.bot_privkey = os.environ.get(
            "POW_PRIVATE_KEY",
            "+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I=",
        )

    def get_vgm(self) -> Path:
        return random.choice(list(Path('music').iterdir()))

    async def create_user(self, username):
        async with httpx.AsyncClient() as c:
            ticket = await self.get_ticket()
            resp = await c.post(f'{self.baseurl_juke}/register', json={
                'Ticket':ticket,
                'User':username
            })
            if resp.status_code != 201:
                raise orderflow.UserCreationError(
                    resp.status_code,
                    resp.text
                )

            data = resp.json()
            logging.info(data)
            username = data[2]
            authtoken = data[3]
            return dict(username=username, authtoken=authtoken)

    async def upload_file(self, username, authtoken, note):
        async with httpx.AsyncClient(follow_redirects=True) as c:
            ticket = await self.get_ticket()
            resp = await c.post(f'{self.baseurl_juke}/login', json={
                'Ticket':ticket,
                'User':username,
                'Token':authtoken
            })
            if resp.status_code > 210:
                raise orderflow.UploadFileError(
                    resp.status_code,
                    resp.text
                )

            file = self.get_vgm()
            vgm = VGM()
            vgm.parse_file(file)
            gd3_offset = vgm.vgm.header.gd3_offset + 24
            gd3_tag = vgm.parsed_info()
            gd3_tag['notes'] = note

            upload_data = vgm.data[:gd3_offset] + \
                vgm.dump_gd3_tag(gd3_tag)
            
            name = secrets.token_urlsafe(10+ secrets.randbelow(10))

            files = {'file': (name + '.vgm', io.BytesIO(upload_data))}
            upload_raw = await c.post(f'{self.baseurl_juke}/file/upload',
                    files=files)
            upload_data = upload_raw.json()
            return upload_data 
 
    async def get_fileinfo(self, username, authtoken, filename, other_user=None):
        async with httpx.AsyncClient(follow_redirects=True) as c:
            ticket = await self.get_ticket()
            resp = await c.post(f'{self.baseurl_juke}/login', json={
                'Ticket':ticket,
                'User':username,
                'Token':authtoken
            })
            if resp.status_code > 210:
                raise orderflow.FileInfoError(
                    resp.status_code,
                    resp.text
                )
            
            url = f'{self.baseurl_juke}/file/info/{filename}'
            if other_user is not None:
                url = f'{url}?User={other_user}'

            info_raw = await c.get(url)
            info_data = info_raw.json()
            return info_data

    async def get_ticket(self):
        ticket_info = None
        ticket_info = await orderflow.get_ticket_async(
            self.baseurl_ticket,
            self.bot_privkey,
            False
        )
        return ticket_info

    async def get_list(self, username, authtoken, fid=None):
        async with httpx.AsyncClient(follow_redirects=True) as c:
            ticket = await self.get_ticket()
            resp = await c.post(f'{self.baseurl_juke}/login', json={
                'Ticket':ticket,
                'User':username,
                'Token':authtoken
            })
            if resp.status_code > 210:
                raise orderflow.FileListError(
                    resp.status_code,
                    resp.text
                )
            
            url = f'{self.baseurl_juke}/file/list/'
            if fid is not None:
                url = f'{url}?from={fid}'

            list_raw = await c.get(url)
            list_data = list_raw.json()
            return list_data

    async def check_file_list(self):
        # Create 1 user, upload a file and then check file list
        username = secrets.token_hex(6 + secrets.randbelow(7))
        userinfo = await self.create_user(username)

        # Upload a file
        upload_data = await self.upload_file(
                userinfo['username'],
                userinfo['authtoken'],
                secrets.token_hex(10 + secrets.randbelow(5))
        )
        file_id = upload_data['file_info'][0]
        file_name = upload_data['filename']

        # Get the list overview
        file_list = await self.get_list(
            userinfo['username'],
            userinfo['authtoken']
        )

        # Check if file is in list
        for f in file_list:
            if f[0] == file_id and f[6] == file_name:
                return

        # If we weren't in list, try again
        file_list = await self.get_list(
            userinfo['username'],
            userinfo['authtoken'],
            fid=file_id
        )

        # Check if file is in list
        for f in file_list:
            if f[0] == file_id and f[6] == file_name:
                return

        raise orderflow.CheckerError(
            CheckResult.FAULTY,
            "Could not find VGM in list"
        )

    async def check_file_list_multiple(self):
        # Check file list with multiple users
        username = secrets.token_hex(6 + secrets.randbelow(7))
        uploader = await self.create_user(username)
        username = secrets.token_hex(6 + secrets.randbelow(7))
        reader =  await self.create_user(username)

        # Upload a file
        upload_data = await self.upload_file(
                uploader['username'],
                uploader['authtoken'],
                secrets.token_hex(10 + secrets.randbelow(5))
        )
        file_id = upload_data['file_info'][0]
        file_name = upload_data['filename']

        # Get the list overview
        file_list = await self.get_list(
            reader['username'],
            reader['authtoken']
        )

        # Check if file is in list
        for f in file_list:
            if f[0] == file_id and f[6] == file_name:
                return

        # If we weren't in list, try again
        file_list = await self.get_list(
            reader['username'],
            reader['authtoken'],
            fid=file_id
        )

        # Check if file is in list
        for f in file_list:
            if f[0] == file_id and f[6] == file_name:
                return

        raise orderflow.CheckerError(
            CheckResult.FAULTY,
            "Can't see VGMs of other users"
        )

    async def check_file_list_no_uploads(self):
        # Check file list with multiple users
        username = secrets.token_hex(6 + secrets.randbelow(7))
        reader = await self.create_user(username)

        # Get the list overview
        file_list = await self.get_list(
            reader['username'],
            reader['authtoken']
        )

        # Check if file is in list
        for f in file_list:
            if f[2] == reader['username']:
                raise orderflow.CheckerError(
                    CheckResult.FAULTY,
                    "Invalid user for VGM file"
                )

    async def check_file_info(self):
        # Check file list with multiple users
        username = secrets.token_hex(6 + secrets.randbelow(7))
        uploader = await self.create_user(username)

        # Upload a file
        note = secrets.token_hex(10 + secrets.randbelow(5))
        upload_data = await self.upload_file(
                uploader['username'],
                uploader['authtoken'],
                note
        )
        file_name = upload_data['filename']

        # Get file info
        file_info = await self.get_fileinfo(
            uploader['username'],
            uploader['authtoken'],
            file_name,
        )

        # Check fields
        if file_info['track'] != upload_data['file_info'][3]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid track name in file info"
            )
        if file_info['game'] != upload_data['file_info'][4]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid game name in file info"
            )
        if file_info['author'] != upload_data['file_info'][5]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid author in file info"
            )
        if file_info['notes'] != note:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid note in file info"
            )

    async def check_file_info_other(self):
        # Check file list with multiple users
        username = secrets.token_hex(6 + secrets.randbelow(7))
        uploader = await self.create_user(username)
        username = secrets.token_hex(6 + secrets.randbelow(7))
        reader = await self.create_user(username)

        # Upload a file
        upload_data = await self.upload_file(
            uploader['username'],
            uploader['authtoken'],
            secrets.token_hex(10 + secrets.randbelow(5))
        )
        file_name = upload_data['filename']

        # Get file info
        file_info = await self.get_fileinfo(
            reader['username'],
            reader['authtoken'],
            file_name,
            uploader['username']
        )

        # Check fields
        expected_note = f"Brought to you by {uploader['username']}" 
        if file_info['track'] != upload_data['file_info'][3]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid track name in file info"
            )
        if file_info['game'] != upload_data['file_info'][4]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid game name in file info"
            )
        if file_info['author'] != upload_data['file_info'][5]:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid author in file info"
            )
        if file_info['notes'] != expected_note:
            raise orderflow.CheckerError(
                CheckResult.FAULTY,
                "Invalid note in file info"
            )

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        # Username 28 bytes max
        username = secrets.token_hex(6 + secrets.randbelow(7))
        userinfo = dict()

        # Try two times
        loop_error = None
        for _ in range(2):
            try:
                userinfo = asyncio.run(self.create_user(username))
                break
            except json.decoder.JSONDecodeError as e:
                logging.warning(e)
                msg = "Invalid user creation response"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.UserCreationError as e:
                logging.warning(e)
                msg = "Error during user creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.TimeoutException as e:
                logging.warning(e)
                msg = "Timeout during user creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.RequestError as e:
                logging.warning(e)
                msg = "Broken request during user creation"
                loop_error = (CheckResult.DOWN, msg)

        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg

        # File upload doesn't happen over CAN, that shouldn't
        # ever fail intentionally
        loop_error = None
        filename = None
        for _ in range(2):
            try:
                upload_data = asyncio.run(
                    self.upload_file(
                        userinfo['username'],
                        userinfo['authtoken'],
                        note=flag + ' ' + secrets.token_hex(4)
                    )
                )
                filename = upload_data['filename']
                break
            except json.decoder.JSONDecodeError as e:
                logging.warning(e)
                msg = "Invalid user creation response"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.UploadFileError as e:
                logging.warning(e)
                msg = "Could not upload file"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.TimeoutException as e:
                logging.warning(e)
                msg = "Timeout during user creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.RequestError as e:
                logging.warning(e)
                msg = "Broken request during user creation"
                loop_error = (CheckResult.DOWN, msg)

        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg
        if not filename:
            msg = "Error during file creation"
            return CheckResult.FAULTY, msg

        flagid = f"{userinfo['username']}/{filename}"
        logging.info("Stored flagid: %s", flagid)
        checkerlib.set_flagid(flagid)
        checkerlib.store_state(f"auth-info_{tick}", userinfo)

        return CheckResult.OK, ""

    def check_service(self) -> Tuple[CheckResult, str]:
        checkers = [
            self.check_file_list,
            self.check_file_list_multiple,
            self.check_file_list_no_uploads,
            self.check_file_info,
            self.check_file_info_other
        ]
        shuffle(checkers)

        for checker in checkers:
            loop_error = None
            for _ in range(2):
                try:
                    asyncio.run(checker())
                    break
                except orderflow.CheckerError as e:
                    logging.warning(e)
                    loop_error = (e.checker_code, e.message)
                except orderflow.FileInfoError as e:
                    logging.warning(e)
                    msg = "Error during file info retrieval"
                    loop_error = (CheckResult.FAULTY, msg)
                except orderflow.FileListError as e:
                    logging.warning(e)
                    msg = "Error during file listing"
                    loop_error = (CheckResult.FAULTY, msg)
                except orderflow.UploadFileError as e:
                    logging.warning(e)
                    msg = "Error during file upload"
                    loop_error = (CheckResult.FAULTY, msg)
                except json.decoder.JSONDecodeError as e:
                    logging.warning(e)
                    msg = "Invalid user creation response"
                    loop_error = (CheckResult.FAULTY, msg)
                except orderflow.TicketEndpointDown as e:
                    logging.warning(e)
                    msg = "Ticket endpoint is down"
                    loop_error = (CheckResult.DOWN, msg)
                except orderflow.TicketCreationError as e:
                    logging.warning(e)
                    msg = "Error during PoW ticket creation"
                    loop_error = (CheckResult.FAULTY, msg)
                except orderflow.UserCreationError as e:
                    logging.warning(e)
                    msg = "Error during user creation"
                    loop_error = (CheckResult.FAULTY, msg)
                except httpx.TimeoutException as e:
                    logging.warning(e)
                    msg = "Timeout during user creation"
                    loop_error = (CheckResult.FAULTY, msg)
                except httpx.RequestError as e:
                    logging.warning(e)
                    msg = "Broken request during user creation"
                    loop_error = (CheckResult.DOWN, msg)

            # If there is an error in the loop, return
            if loop_error is not None:
                status, msg = loop_error
                return status, msg

        # If all checkers passed we're good
        return CheckResult.OK, ""

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)
        userinfo = checkerlib.load_state(f"auth-info_{tick}")

        logging.warning(f"Using Flagid: [{flagid}]")

        if not flagid:
            logging.info("No flagid saved for this team and tick")
            return (
                CheckResult.FLAG_NOT_FOUND,
                "flag was not placed successfully",
            )

        # Try two times
        loop_error = None
        fileinfo = None
        for _ in range(2):
            try:
                fileinfo = asyncio.run(
                    self.get_fileinfo(
                        userinfo['username'],
                        userinfo['authtoken'],
                        flagid.split('/')[1]
                    )
                )
                break
            except orderflow.FileInfoError as e:
                logging.warning(e)
                msg = "Error during file info retrieval"
                loop_error = (CheckResult.FAULTY, msg)
            except json.decoder.JSONDecodeError as e:
                logging.warning(e)
                msg = "Invalid user creation response"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.UserCreationError as e:
                logging.warning(e)
                msg = "Error during user creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.TimeoutException as e:
                logging.warning(e)
                msg = "Timeout during user creation"
                loop_error = (CheckResult.FAULTY, msg)
            except httpx.RequestError as e:
                logging.warning(e)
                msg = "Broken request during user creation"
                loop_error = (CheckResult.DOWN, msg)
        
        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg

        if fileinfo is not None and flag in fileinfo.get('notes'):
            return CheckResult.OK, ""
        return CheckResult.FLAG_NOT_FOUND, "flag was not in response"


if __name__ == "__main__":
    checkerlib.run_check(CantinaChecker2)

