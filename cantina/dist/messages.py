from abc import abstractclassmethod, abstractmethod
from enum import IntEnum
import can
import msgpack
from typing import List, Tuple


class ToCanMsgType(IntEnum):
    UNDEFINED = 0
    CAN_FRAME = 1
    CAN_FILTER = 2
    CAN_QUOTA = 3
    CAN_TOKEN = 4
    CAN_ERROR = 5


def load_message(data):
    msg_type, payload = data
    if msg_type == ToCanMsgType.UNDEFINED:
        return Undefined.unpack(payload)
    elif msg_type == ToCanMsgType.CAN_FRAME:
        return CanFrame.unpack(payload)
    elif msg_type == ToCanMsgType.CAN_FILTER:
        return CanFilter.unpack(payload)
    elif msg_type == ToCanMsgType.CAN_QUOTA:
        return CanQuota.unpack(payload)
    elif msg_type == ToCanMsgType.CAN_TOKEN:
        return CanToken.unpack(payload)
    elif msg_type == ToCanMsgType.CAN_ERROR:
        return CanError.unpack(payload)
    raise ValueError("Unknown Message Type")


class ToCanMessage:
    def __init__(self, msg_type):
        self.msg_type = msg_type

    @abstractclassmethod
    def unpack(cls, data):
        raise NotImplementedError("This should be implemented")

    @abstractmethod
    def pack(cls):
        raise NotImplementedError("This should be implemented")


class Undefined(ToCanMessage):
    def __init__(self, hello):
        super(Undefined, self).__init__(ToCanMsgType.UNDEFINED)
        self.hello = hello

    @classmethod
    def unpack(cls, data):
        return cls(data)

    def pack(self):
        message = msgpack.packb([self.msg_type, self.hello])
        return message

    def __str__(self):
        return f"[{self.msg_type}]: {self.hello}"

class CanFrame(ToCanMessage):
    def __init__(self, can_message):
        super(CanFrame, self).__init__(ToCanMsgType.CAN_FRAME)
        self.can_message = can_message

    @classmethod
    def unpack(cls, data):
        data_length = int.from_bytes(data[4:8], byteorder='little')
        is_fd = False
        if data_length > 8:
            is_fd = True
        arb_id = int.from_bytes(data[:4], byteorder='little')
        is_extended = False
        if arb_id & 0x80000000 > 0:
            is_extended = True
            arb_id &= 0x1FFFFFFF
        else:
            is_extended = False
            arb_id &= 0x000007FF
        can_message = can.Message(check=True, 
                                  arbitration_id=arb_id,
                                  is_fd = is_fd,
                                  data = data[8:8+data_length])
        return cls(can_message)

    def pack(self):
        arb_id = self.can_message.arbitration_id
        if arb_id >= 0x800:
            arb_id |= 0x80000000
        arb_id = arb_id.to_bytes(4, byteorder='little')
        msg_len = len(self.can_message.data).to_bytes(4, byteorder='little')

        message = msgpack.packb([self.msg_type, arb_id + msg_len + self.can_message.data])
        return message

    def __eq__(self, canframe):
        return self.can_message.equals(canframe.can_message, timestamp_delta=None)

    def __contains__(self, canframe):
        return self.can_message.equals(canframe.can_message, timestamp_delta=None)

    def __str__(self):
        return f"[{self.msg_type}]: {self.can_message}"


class CanFilter(ToCanMessage):
    def __init__(self, filters: List[Tuple[int,int]]):
        super(CanFilter, self).__init__(ToCanMsgType.CAN_FILTER)
        self.filters = filters

    @classmethod
    def unpack(cls, data):
        filters = []
        for i in range(0, len(data), 2):
            filters.append((data[i], data[i+1]))
        filters
        return cls(filters)

    def pack(self):
        message = msgpack.packb([self.msg_type, self.filters])
        return message
    
    def __str__(self):
        return f"[{self.msg_type}]: {self.filters}"

class CanToken(ToCanMessage):
    def __init__(self, token):
        super(CanToken, self).__init__(ToCanMsgType.CAN_TOKEN)
        self.token = token

    @classmethod
    def unpack(cls, data):
        return cls(data)

    def pack(self):
        message = msgpack.packb([self.msg_type, self.token])
        return message

    def __str__(self):
        return f"[{self.msg_type}]: {self.token}"


class CanQuota(ToCanMessage):
    def __init__(self, quota):
        super(CanQuota, self).__init__(ToCanMsgType.CAN_QUOTA)
        self.quota = quota

    @classmethod
    def unpack(cls, data):
        quota = int.from_bytes(data,"little")
        return cls(quota)

    def pack(self):
        message = msgpack.packb([self.msg_type, self.quota])
        return message
    
    def __str__(self):
        return f"[{self.msg_type}]: {self.quota}"

class CanError(ToCanMessage):
    def __init__(self, error):
        super(CanError, self).__init__(ToCanMsgType.CAN_ERROR)
        self.error = error

    @classmethod
    def unpack(cls, data):
        return cls(data)

    def pack(self):
        message = msgpack.packb([self.msg_type, self.error])
        return message

    def __str__(self):
        return f"[{self.msg_type}]: {self.error}"

