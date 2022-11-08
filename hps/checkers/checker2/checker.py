#!/usr/bin/env python3

import hashlib
import json
import logging
import random
import socket
import time
from typing import Tuple

import requests
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


# valve
import paho.mqtt.client as mqtt
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from firmware_generator import generate_upload_firmware


class HPSChecker2(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10031
        self.mqtt_port = 10036
        self.timeout = 15 # don't forget to set a timeout for every requests you send
        self.baseurl = f'http://{self.ip}:{self.port}'
        self.background_data = {}
        self.background_data_tick = -1
        self.history = {}
        s = requests.Session()
        Retry.DEFAULT_BACKOFF_MAX = 10
        retries = Retry(total=2,
                        backoff_factor=5,
                        status_forcelist=[500, 502, 503, 504])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        self.session = s


    def get_mqtt_connection(self):
        client = mqtt.Client()
        client.tls_set("/ca.crt", "/commander.crt", "/commander.key")
        client.tls_insecure_set(True)

        client.connect(self.ip, self.mqtt_port, self.timeout)
        return client

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:

        checkerlib.store_state("valve_current_tick", tick)

        valve_position = random.randint(0, 100)
        operator = checkerlib.get_flag(tick)
        data = {
            "valve_position": valve_position,
            "operator": operator,
            "packet_id": tick
        }
        valve_data = checkerlib.load_state("valve_data")
        if not valve_data:
            valve_data = {}
        valve_data[tick] = data
        checkerlib.store_state("valve_data", valve_data)
        try:
            client = self.get_mqtt_connection()
        except Exception as e:
            logging.exception('could not connect to mqtt')
            return CheckResult.FAULTY, 'could not connect to mqtt'

        resp = client.publish("valve/commands", json.dumps({"command": "control", "data": data}))
        resp.wait_for_publish(timeout=self.timeout)
        client.disconnect()

        if resp.is_published() is False:
            logging.warning('Could not publish to mqtt')
            return CheckResult.FAULTY, 'Could not publish to mqtt'

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        tick = checkerlib.load_state("valve_current_tick")
        res = generate_upload_firmware(f"{self.baseurl}/firmware_upgrade", tick=tick, checker_instance=self)
        if res["response"] != 200:
            logging.info('1-Could not upload firmware')
            return CheckResult.FAULTY, 'could not upload firmware'
        version_hash = res["version_hash"]
        time.sleep(2)
        resp = self.session.get(f"{self.baseurl}/", timeout=self.timeout)
        if resp.status_code != 200:
            return CheckResult.FAULTY, 'could not get status'
        if version_hash not in resp.text:
            return CheckResult.FAULTY, 'wrong version'

        resp = self.session.get(f"{self.baseurl}/command_logs", timeout=self.timeout)
        if resp.status_code != 200:
            return CheckResult.FAULTY, 'could not get command_logs'
        if "Received command" not in resp.text:
            return CheckResult.FAULTY, 'wrong command_logs'
        return CheckResult.OK, ''

    def on_message(self, client, userdata, msg):
        self.background_data = json.loads(msg.payload.decode("utf-8")).get("command_history")

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        logging.info("Checking flag, tick %s", tick)
        valve_data = checkerlib.load_state("valve_data")
        if not valve_data:
            logging.error("No valve data")
            return CheckResult.FLAG_NOT_FOUND, 'no data for tick'
        if tick not in valve_data:
            logging.error("No valve data for tick %s", tick)
            return CheckResult.FLAG_NOT_FOUND, 'no data for tick'
        data = {'command': 'control', 'data': valve_data[tick]}
        flag = checkerlib.get_flag(tick)
        to_hash = " - instruction_log - INFO - Received command: " + str(data)
        md5 = hashlib.md5(to_hash.encode('utf-8')).hexdigest()
        res = self.session.get(f"{self.baseurl}/command_logs", timeout=self.timeout)
        if md5 not in res.text:
            return CheckResult.FLAG_NOT_FOUND, 'flag not found'

        if self.background_data_tick < tick:
            logging.info("Getting background data, cache miss")
            try:
                client = self.get_mqtt_connection()
            except Exception as e:
                logging.exception('could not connect to mqtt')
                return CheckResult.FAULTY, 'could not connect to mqtt'
            client.on_message = self.on_message
            self.background_data = {}
            client.subscribe("valve/status")
            client.loop_start()
            client.publish("valve/commands", json.dumps({"command": "command_history"}))
            for i in range(0, 10):
                if len(self.background_data) > 0:
                    break
                time.sleep(1)
                client.publish("valve/commands", json.dumps({"command": "command_history"}))
            client.loop_stop()
            client.disconnect()
            if len(self.background_data) == 0:
                logging.info('No history data received')
                return CheckResult.FAULTY, 'no history data received'
            self.background_data_tick = tick
        if flag not in self.background_data:
            logging.info('Cant find flag %s', tick)
            return CheckResult.FLAG_NOT_FOUND, 'Cant find flag %s'

        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(HPSChecker2)
