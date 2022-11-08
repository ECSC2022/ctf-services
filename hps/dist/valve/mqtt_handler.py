import datetime
import os
import subprocess
import threading
import time
import paho.mqtt.client as mqtt
import json

import settings
from configuration import ConfigSingleton


class MqttClient(threading.Thread):
    def __init__(self, broker, port, timeout, topics):
        super(MqttClient, self).__init__()
        self.client = None
        self.broker = broker
        self.port = port
        self.timeout = timeout
        self.topics = topics
        self._stop = threading.Event()

    #  run method override from Thread class
    def run(self):
        while not self._stop.is_set():
            try:
                self.connect_to_broker()
            except Exception as e:
                print("Critical connection in mqtt thread, retrying in 5 seconds")
                print(e)
                import traceback
                traceback.print_exc()
                time.sleep(5)

    def connect_to_broker(self):
        self.client = mqtt.Client()

        self.client.username_pw_set("valve", settings.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.connect(self.broker, self.port, self.timeout)
        self.client.on_message = self.on_message
        self.client.loop_start()
        time.sleep(2)
        while self.client.is_connected() and not self._stop.is_set():
            time.sleep(1)
        self.client.loop_stop()
        self.client.disconnect()
        self.client = mqtt.Client()
        print("Disconnected from broker")

    def on_message(self, client, userdata, msg):
        try:
            if msg.topic != "valve/commands":
                return
            data = json.loads(msg.payload.decode("utf-8"))
            print("Received message: " + str(data))
            if data["command"] == "control":
                from app import command_logger
                command_logger.info("Received command: " + str(data))
                s = ConfigSingleton()
                s.position = data["data"]["valve_position"]
                s.save()
                print("Processed command")
            elif data["command"] == "command_history":
                from app import command_log_file
                lines = subprocess.check_output(['tail', '-100', command_log_file]).decode('utf-8')

                self.client.publish("valve/status", json.dumps({"command_history": lines}))
                print("Received ping from server")
        except Exception as e:
            print("Error in on_message")
            print(e)
            import traceback
            traceback.print_exc()

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        #  Subscribe to a list of topics using a lock to guarantee that a topic is only subscribed once
        for topic in self.topics:
            client.subscribe(topic)
            print("Subscribed to topic: " + topic)