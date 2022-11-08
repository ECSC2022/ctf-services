import json
import os
import threading


class ConfigSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                # another thread could have created the instance
                # before we acquired the lock. So check that the
                # instance is still nonexistent.
                if not cls._instance:
                    cls._instance = super(ConfigSingleton, cls).__new__(cls)
        return cls._instance

    def save(self):
        with open("config.json", "w") as f:
            data = {
                "position": self.position,
                "water_temperature": self.water_temperature,
                "mode": self.mode,
                "command_source": self.command_source,
                "voltage": self.voltage,
                "defrosting": self.defrosting,
                "defrosting_status": self.defrosting_status
            }
            json.dump(data, f)

    def load(self):
        with open("config.json", "r") as f:
            data = json.load(f)
            self.position = data["position"]
            self.water_temperature = data["water_temperature"]
            self.mode = data["mode"]
            self.command_source = data["command_source"]
            self.voltage = data["voltage"]
            self.defrosting = data["defrosting"]
            self.defrosting_status = data["defrosting_status"]

    def __init__(self):
        self.position = 30
        self.water_temperature = 20
        self.mode = "automatic"
        self.command_source = "MQTT"
        self.voltage = 12.1
        self.defrosting = False
        self.defrosting_status = "Ready"
        if os.path.exists("config.json"):
            self.load()

