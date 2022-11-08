import json

from django.db import models


class DataLog(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    _raw = models.TextField()
    voltage = models.FloatField()
    current = models.FloatField()
    frequency = models.FloatField()
    phase_shift = models.FloatField()
    apparent_power = models.IntegerField()  # active_power + reactive power = apparent_power
    reactive_power = models.IntegerField()
    active_power = models.IntegerField()
    current_electricity_meter_reading = models.FloatField()

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'voltage': self.voltage,
            'current': self.current,
            'frequency': self.frequency,
            'phase_shift': self.phase_shift,
            'apparent_power': self.apparent_power,
            'reactive_power': self.reactive_power,
            'active_power': self.active_power,
            'current_electricity_meter_reading': self.current_electricity_meter_reading,
            '_raw': self._raw
        }

    def __str__(self):
        return json.dumps(self.to_dict(), default=str)
