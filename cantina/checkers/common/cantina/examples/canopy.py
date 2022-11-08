#!/usr/bin/env python3
import asyncio
import logging
import can

from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305 as AEAD

from cantina import Cipher
from cantina.canopy import Client, Server


if __name__ == '__main__':
    import sys
    import yaml

    logging.basicConfig(level=logging.INFO)

    # Load message ID config
    msg_ids = dict()
    with open(sys.argv[1]) as f:
        msg_ids = yaml.load(f.read(), yaml.CSafeLoader)

    shared_key = bytes([0x41] * 32)
    aead = AEAD(shared_key)
    cipher = Cipher()
    cipher.update(aead)

    with can.ThreadSafeBus(
        channel=sys.argv[2],
        interface='socketcan',
        fd=True
    ) as bus:
        if sys.argv[3] == 'send':
            async def main() -> None:
                # Setup send queue
                send_queue = asyncio.Queue()

                # Setup receive queue through a notifier
                recv_queue = can.AsyncBufferedReader()
                loop = asyncio.get_running_loop()
                notifier = can.Notifier(bus, [recv_queue], loop=loop)
                
                # Setup our server components
                canopy_client = Client(cipher, send_queue, {
                    'canopy_start': msg_ids['MSGID_POS_ORDER_START'],
                    'canopy_data': msg_ids['MSGID_POS_ORDER_DATA'],
                    'canopy_reply_start': \
                        msg_ids['MSGID_POS_ORDER_REPLY_START'],
                    'canopy_reply_data': \
                        msg_ids['MSGID_POS_ORDER_REPLY_DATA']
                })

                # Background task for sending messages
                async def send_can_messages(q, b: can.Bus):
                    while True:
                        msg = await q.get()
                        b.send(msg)
                        q.task_done()

                # Background task for receiving messages
                async def recv_can_messages(r):
                    handlers = canopy_client.recv_handlers()
                    while msg := await r.get_message():
                        mid = msg.arbitration_id
                        if mid in handlers:
                            await handlers[mid](msg)

                # Start background tasks
                tasks = [
                    asyncio.create_task(send_can_messages(
                        send_queue, bus)),
                    asyncio.create_task(recv_can_messages(
                        recv_queue))
                ]
                
                # Send messages with our client
                logging.info(await canopy_client.send(b'A' * 5000))

                # Wait for background tasks
                #asyncio.gather(*tasks)
                await tasks[0]

                # Clean-up
                notifier.stop()

            asyncio.run(main())
        else:
            async def main() -> None:
                # Setup send queue
                send_queue = asyncio.Queue()

                # Setup receive queue through a notifier
                recv_queue = can.AsyncBufferedReader()
                loop = asyncio.get_running_loop()
                notifier = can.Notifier(bus, [recv_queue], loop=loop)
                
                # Setup our server components
                canopy_server = Server(cipher, send_queue, {
                    'canopy_start': msg_ids['MSGID_POS_ORDER_START'],
                    'canopy_data': msg_ids['MSGID_POS_ORDER_DATA'],
                    'canopy_reply_start': \
                        msg_ids['MSGID_POS_ORDER_REPLY_START'],
                    'canopy_reply_data': \
                        msg_ids['MSGID_POS_ORDER_REPLY_DATA']
                })

                # Background task for sending messages
                async def send_can_messages(q, b: can.Bus):
                    while True:
                        msg = await q.get()
                        b.send(msg)
                        q.task_done()

                # Background task for receiving messages
                async def recv_can_messages(r):
                    handlers = canopy_server.recv_handlers()
                    while msg := await r.get_message():
                        mid = msg.arbitration_id
                        if mid in handlers:
                            await handlers[mid](msg)

                # Start background tasks
                tasks = [
                    asyncio.create_task(send_can_messages(
                        send_queue, bus)),
                    asyncio.create_task(recv_can_messages(
                        recv_queue)),
                    asyncio.create_task(canopy_server.update_loop())
                ]
                
                # Wait for background tasks
                #asyncio.gather(*tasks)
                #await tasks[0]
                await asyncio.wait(tasks)

                # Clean-up
                notifier.stop()

            asyncio.run(main())

