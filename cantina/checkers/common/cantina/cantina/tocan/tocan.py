from asyncio.tasks import FIRST_COMPLETED, FIRST_EXCEPTION
from abc import abstractmethod
import janus
import msgpack
import can
import asyncio
import queue
from threading import Thread
import socket
import time
from enum import IntEnum
from pathlib import Path

from typing import List, Literal

from collections import deque

from multiprocessing import Process, Queue

from .message import ToCanMessage, CanFrame, CanError, load_message


def pack_can_message(msg: can.Message):
    msg.channel = "tocan"
    can_frame = CanFrame(msg)
    return can_frame.pack()

class ToCan:
    def __init__(self):
        self.messages_in = janus.Queue()
        self.messages_out = janus.Queue()

    async def _recv(self, reader):
        unpacker = msgpack.Unpacker(max_buffer_size=1024)
        while not reader.at_eof():
            data = await reader.read(256)
            unpacker.feed(data)
            for data in unpacker:
                msg = load_message(data)
                await self._handle(msg)

    @abstractmethod
    async def _handle(self, msg: ToCanMessage):
        raise NotImplementedError("Need to implement handler function")

    async def _send(self, writer):
        while msg := await self.messages_out.async_q.get():
            writer.write(msg)
            await writer.drain()
            self.messages_out.async_q.task_done()

    async def recv(self):
        data = await self.messages_in.async_q.get()
        self.messages_in.sync_q.task_done()
        return data

    def recv_sync(self):
        data = self.messages_in.sync_q.get()
        self.messages_in.sync_q.task_done()
        return data

    async def send(self, msg: can.Message):
        return await self.messages_out.async_q.put(pack_can_message(msg))

    def send_sync(self, msg: can.Message):
        return self.messages_out.sync_q.put(pack_can_message(msg))

    async def send_msg(self, msg: ToCanMessage):
        return await self.messages_out.async_q.put(msg.pack())

    def send_msg_sync(self, msg: ToCanMessage):
        return self.messages_out.sync_q.put(msg.pack())

    async def send_raw(self, msg: bytes):
        return await self.messages_out.async_q.put(msg)

    def send_raw_sync(self, msg: bytes):
        return self.messages_out.sync_q.put(msg)

    async def start(self, reader, writer, additional_tasks=[]):
        receiver = asyncio.create_task(self._recv(reader))
        sender = asyncio.create_task(self._send(writer))
        tasks = [receiver, sender] + additional_tasks
        try:
            done, pending = await asyncio.wait(tasks, return_when=FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            writer.close()
            await writer.wait_closed()


class ToCanClient(ToCan):
    def __init__(self, host, port, bot_privkey=None, receive_own_messages=False):
        super(ToCanClient, self).__init__()
        self.host = host
        self.port = port
        self.receive_own_messages = receive_own_messages

    async def connect(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        end = await self.start(reader, writer)
        raise Exception("Connection closed")

    async def _handle(self, msg: ToCanMessage):
        await self.messages_in.async_q.put(msg)

       # if isinstance(msg, CanFrame):
       #     can_message = msg.can_message
       #     await self.messages_in.async_q.put(can_message)
       # elif isinstance(msg, CanError):
       #     print("CAN Error")
       # else:
       #     print("Unexpected: ", msg)

    async def _send(self, writer):
        while msg := await self.messages_out.async_q.get():
            writer.write(msg)
            await writer.drain()
            self.messages_out.async_q.task_done()


#class ToCanHandler(ToCan):
#    def __init__(self, bot_pubkey):
#        super(ToCanHandler, self).__init__()
#
#        self.pow = PoW(POW_DIFFICULTY, bot_pubkey=bot_pubkey)
#        self.pow_targets = deque()
#        self.pow_queue = asyncio.Queue(30)
#
#    async def _handle(self, msg: ToCanMessage):
#        if isinstance(msg, CanFrame):
#            can_message = msg.can_message
#            self.pow_queue.put_nowait(can_message)
#            pow_message, target = self.pow.generate()
#            self.pow_targets.append(target)
#            pow_request = PoWRequest(pow_message)
#            await self.send_msg(pow_request)
#        elif isinstance(msg, PoWResponse):
#            pow_solution = msg.pow_solution
#            self.pow.verify(self.pow_targets.popleft(), pow_solution)
#            msg = self.pow_queue.get_nowait()
#            await self.messages_in.async_q.put(msg)
#            self.pow_queue.task_done()
#        else:
#            print("Unexpected:", msg)
#
#
#class ToCanServer:
#    def __init__(self, host, port, can_interface, bot_pubkey):
#        super(ToCanServer, self).__init__()
#        self.host = host
#        self.port = port
#        self.can_bus = ToCanBus(can_interface)
#        self.bot_pubkey = bot_pubkey
#
#    async def serve(self):
#        try:
#            server = await asyncio.start_server(
#                self._handle_client, self.host, self.port
#            )
#            self.can_bus.start()
#            relay = asyncio.create_task(self.can_bus.relay_to_clients())
#            serve = asyncio.create_task(server.serve_forever())
#            await asyncio.wait({serve, relay}, return_when=asyncio.FIRST_COMPLETED)
#        finally:
#            self.can_bus.stop()
#            self.can_bus.join()
#
#    async def _handle_client(self, reader, writer):
#        client = ToCanHandler(self.bot_pubkey)
#        self.can_bus.add_client(client)
#        try:
#            await client.start(reader, writer)
#        except socket.error as e:
#            print(e)
#        finally:
#            self.can_bus.remove_client(client)
#
#
#class ToCanBus(Thread):
#    def __init__(self, interface, receive_own_messages=True):
#        super(ToCanBus, self).__init__()
#        self.interface = interface
#        self.can_out = janus.Queue()
#        self.can_in = janus.Queue()
#        self.clients: List[ToCan] = list()
#        self.receive_own_messages = receive_own_messages
#
#    def stop(self):
#        self.can_in.sync_q.put_nowait(None)
#
#    def run(self):
#        canBus = can.Bus(
#            interface="socketcan",
#            channel=self.interface,
#            receive_own_messages=self.receive_own_messages,
#            fd=True,
#        )
#        listeners = [self._on_can_msg_recv]
#        notifier = can.Notifier(canBus, listeners)
#        try:
#            while msg := self.can_in.sync_q.get():
#                if msg == None:
#                    self.can_in.sync_q.task_done()
#                    return
#                canBus.send(msg)
#                self.can_in.sync_q.task_done()
#        finally:
#            notifier.stop()
#            canBus.shutdown()
#
#    def add_client(self, tocan: ToCan):
#        tocan.messages_in = self.can_in
#        self.clients.append(tocan)
#
#    def remove_client(self, tocan: ToCan):
#        self.clients.remove(tocan)
#
#    def _on_can_msg_recv(self, msg):
#        self.can_out.sync_q.put(msg)
#
#    async def relay_to_clients(self):
#        tasks = []
#        while msg := await self.can_out.async_q.get():
#            msg.timestamp = time.time()
#            can_message = pack_can_message(msg)
#            for client in self.clients:
#                tasks.append(asyncio.create_task(client.send_raw(can_message)))
#            self.can_out.async_q.task_done()
#            await asyncio.gather(*tasks)
