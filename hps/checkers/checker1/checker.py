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


# Smartmeter
import paho.mqtt.client as mqtt


class HPSChecker1(checkerlib.BaseChecker):

    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.port = 10030
        self.mqtt_port = 10036
        self.timeout = 15 # don't forget to set a timeout for every requests you send
        self.baseurl = f'http://{self.ip}:{self.port}'
        self.background_data = {}

    def calculate_new_value(self, current, baseline, decimals=1, min_value=0.0, max_value=100.0, min_offset=1.2):
        offset = current - baseline
        if offset < 0:
            offset *= -1
        offset *= (10 ** decimals)
        offset = int(offset)
        offset = max(min_offset * (10 ** decimals), offset)
        current = round(current + (random.randint(offset * -1, offset) / (10 ** decimals)), decimals)
        current = max(min_value, current)
        current = min(max_value, current)
        return current

    def generate_base_data(self, tick: int):
        data = checkerlib.load_state("smartmeter")
        data_history = checkerlib.load_state("smartmeter_history")
        if data_history is None:
            data_history = {}
        if data is None:
            data = {
                "baseline": {
                    "voltage": 220.0,
                    "current": 16.0,
                    "frequency": 50.01,
                    "phase_shift": 0.5,
                }
            }
            data.update(**data["baseline"])
            data["current_electricity_meter_reading"] = 0.0
        if tick == -1:
            return data
        if data.get("tick", -1) == tick:
            return data
        if data.get("tick", -1) > tick:
            if tick in data_history:
                return data_history[tick]
        data_history[data.get("tick", -1)] = data
        if len(data_history.keys()) > 50:
            data_history.pop(min(data_history.keys()))
        checkerlib.store_state("smartmeter_history", data_history)

        data["voltage"] = self.calculate_new_value(data["voltage"], data["baseline"]["voltage"], decimals=1,
                                                   min_value=200, max_value=240, min_offset=1.2)
        data["current"] = self.calculate_new_value(data["current"], data["baseline"]["current"], decimals=1,
                                                   min_value=4, max_value=20, min_offset=1.5)
        data["frequency"] = self.calculate_new_value(data["frequency"], data["baseline"]["frequency"], decimals=2,
                                                     min_value=49.70, max_value=51.21, min_offset=0.05)
        data["phase_shift"] = self.calculate_new_value(data["phase_shift"], data["baseline"]["phase_shift"], decimals=1,
                                                       min_value=-10, max_value=10, min_offset=0.5)
        data["tick"] = tick
        data["current_electricity_meter_reading"] += int(data["voltage"] * data["current"]) / 1000.0 / 20 # a tick is 3 minutes, 60/3 = 20
        checkerlib.store_state("smartmeter", data)

        return data

    def generate_data(self, tick: int):
        data = self.generate_base_data(tick)
        if tick == -1:
            tick = data["tick"]
        data["flag"] = checkerlib.get_flag(tick)
        data["apparent_power"] = int(data["voltage"] * data["current"])
        data["reactive_power"] = int(data["apparent_power"] * 0.15)
        data["active_power"] = int(data["apparent_power"] * 0.85)
        del data["baseline"]
        return data

    def get_mqtt_connection(self):
        client = mqtt.Client()
        client.tls_set("/ca.crt", "/commander.crt", "/commander.key")
        client.tls_insecure_set(True)

        client.connect(self.ip, self.mqtt_port, self.timeout)
        return client

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        try:
            client = self.get_mqtt_connection()
        except Exception as e:
            logging.exception('could not connect to mqtt')
            return CheckResult.FAULTY, 'could not connect to mqtt'
        data = self.generate_data(tick)
        resp = client.publish("smartmeter/commands", json.dumps({"command": "readings", "data": data}))
        resp.wait_for_publish(timeout=self.timeout)
        client.disconnect()

        if resp.is_published() is False:
            logging.warning('Could not publish to mqtt')
            return CheckResult.FAULTY, 'Could not publish to mqtt'

        return CheckResult.OK, ''

    def check_service(self) -> Tuple[CheckResult, str]:
        resp = requests.get(self.baseurl + "/current_readings", timeout=self.timeout)

        if resp.status_code != 200:
            logging.info('1-Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'
        content = resp.content.decode("utf-8").split("<span class=\"badge badge-primary badge-pill\" id=\"hash\">")[1].split("</span>")[0]
        sha_hash = hashlib.md5()
        data = self.generate_data(-1)
        sha_hash.update(json.dumps(data).encode("utf-8"))
        hash_digest = sha_hash.hexdigest()
        if content != hash_digest:
            logging.info('Got incorrect hash %s, expected %s', content, hash_digest)
            return CheckResult.FAULTY, 'incorrect hash-data tampered'

        if data["tick"] < 1:
            return CheckResult.OK, ''
        target = random.choice(["render_graph_phase_shift_svg", "render_graph_voltage_svg"])
        resp = requests.get(self.baseurl + f"/{target}/", timeout=self.timeout)
        if resp.status_code != 200:
            logging.info('2-Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'
        if resp.content.decode("utf-8").find("svg") == -1:
            logging.info('3-Got incorrect response')
            return CheckResult.FAULTY, 'incorrect response'
        if resp.content.decode("utf-8").find("stroke:#00aaaa") == -1:
            logging.info('4-Got incorrect response')
            return CheckResult.FAULTY, 'incorrect response'

        target = random.choice(["render_graph_current_png", "render_graph_power_png"])
        resp = requests.get(self.baseurl + f"/{target}/", timeout=self.timeout)
        if resp.status_code != 200:
            logging.info('5-Got incorrect status code %s', resp.status_code)
            return CheckResult.FAULTY, 'incorrect status code'
        if b"PNG" not in resp.content:
            logging.info('6-Got incorrect response')
            return CheckResult.FAULTY, 'incorrect response'

        target = "render_graph_frequency_html"
        resp = requests.get(self.baseurl + f"/{target}/", timeout=self.timeout)
        if resp.status_code != 200:
            logging.info('7-Got incorrect status code %s, ignoring', resp.status_code)
        if resp.content.decode("utf-8").find("iFrame") == -1:
            logging.info('8-Got incorrect response, ignoring')
        if resp.content.decode("utf-8").find("BokehJS library") == -1:
            logging.info('9-Got incorrect response, ignoring')
        return CheckResult.OK, ''

    def on_message(self, client, userdata, msg):
        self.background_data = json.loads(msg.payload.decode("utf-8"))

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        expected_data = self.generate_data(tick)
        if str(tick) not in self.background_data:
            try:
                client = self.get_mqtt_connection()
            except Exception as e:
                logging.exception('1-could not connect to mqtt')
                return CheckResult.FAULTY, 'could not connect to mqtt'
            client.on_message = self.on_message
            self.background_data = {}
            client.subscribe("smartmeter/status")
            client.loop_start()
            client.publish("smartmeter/commands", json.dumps({"command": "history"}))
            for i in range(0, 10):
                if len(self.background_data) > 0:
                    break
                time.sleep(1)
            client.loop_stop()
            client.disconnect()
            if len(self.background_data) == 0:
                logging.info('2-No history data received')
                return CheckResult.FAULTY, 'no history data received'
        if str(tick) not in self.background_data:
            logging.info('3-No data for tick %s', tick)
            return CheckResult.FLAG_NOT_FOUND, 'no data for tick'
        data_raw = self.background_data[str(tick)]
        if data_raw.get("flag", "") != expected_data["flag"]:
            logging.info('4-Got wrong flag: %s', data_raw.get("flag", ""))
            return CheckResult.FLAG_NOT_FOUND, 'wrong flag'

        return CheckResult.OK, ''


if __name__ == '__main__':
    checkerlib.run_check(HPSChecker1)
