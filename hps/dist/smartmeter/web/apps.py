import json
import random
import threading
import time

from django.apps import AppConfig
from django.apps import AppConfig
from threading import Thread
import paho.mqtt.client as mqtt


class MqttClient(Thread):
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
                time.sleep(5)

    def connect_to_broker(self):
        from web.models import DataLog

        self.client = mqtt.Client()

        self.client.tls_set("ca.crt", "smartmeter.crt", "smartmeter.key")
        self.client.tls_insecure_set(True)

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
            if msg.topic != "smartmeter/commands":
                return
            data = json.loads(msg.payload.decode("utf-8"))
            print("Received message: " + str(data))
            if data["command"] == "readings":
                json_data = json.dumps(data["data"])
                from web.models import DataLog
                data = data["data"]
                d = DataLog(_raw=json_data,
                            voltage=data["voltage"],
                            current=data["current"],
                            frequency=data["frequency"],
                            phase_shift=data["phase_shift"],
                            apparent_power=data["apparent_power"],
                            reactive_power=data["reactive_power"],
                            active_power=data["active_power"],
                            current_electricity_meter_reading=data["current_electricity_meter_reading"])
                d.save()
                print("Saved data to database")
            elif data["command"] == "history":
                from web.models import DataLog
                d = list(DataLog.objects.order_by('-timestamp')[:10])
                resp = {}
                for dd in d:
                    ddd = json.loads(dd._raw)
                    resp[ddd.get("tick", -1)] = ddd
                self.client.publish("smartmeter/status", json.dumps(resp))
                print("Received ping from server")
        except Exception as e:
            print(e)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        #  Subscribe to a list of topics using a lock to guarantee that a topic is only subscribed once
        for topic in self.topics:
            client.subscribe(topic)
            print("Subscribed to topic: " + topic)


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'

    def __init__(self, *args, **kwargs):
        self.mqtt_client = None
        super().__init__(*args, **kwargs)
        print("WebConfig.__init__()")

    def ready(self):
        print("WebConfig.ready()")
        if not self.mqtt_client or not self.mqtt_client.is_alive():
            self.mqtt_client = MqttClient('hps-mqtt', 10036, 60, ['smartmeter/commands'])
            self.mqtt_client.daemon = True
            self.mqtt_client.start()
            print("MQTT client started")
        else:
            print("MQTT client already started")
