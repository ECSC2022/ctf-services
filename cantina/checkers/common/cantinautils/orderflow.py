import base64
import yaml
import json
import cantina
import httpx
import asyncio
import os
import random

from cantina.powcheck import powcheck
from cantina.tocan import ToCanClient
from cantina.tocan.message import *
from cantina.canopy.fields import Session
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


POW_HARDNESS = 21
POW_PRIVATE_KEY = "+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I="
CONF_DIR = '/conf'


class CantinaError(Exception):
    pass


class TicketCreationError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class TicketEndpointDown(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class PoWEndpointError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class ItemEndpointError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class OrderCreationError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class OrderRetrievalError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class UserCreationError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class UploadFileError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class FileInfoError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class FileListError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


class CheckerError(CantinaError):
    def __init__(self, checker_code, message):
        self.message = message
        self.checker_code = checker_code
        super().__init__(f'{self.checker_code}: {self.message}')


def json_error(r):
    try:
        return r.json()['error']
    except json.JSONDecodeError:
        return r.text


async def get_ticket_async(
    base_url, bot_priv_key_b64, simulsleep=False
):
    # TODO: Random user agent
    headers = {"user-agent": "python-requests/2.28.1"}

    try:
        async with httpx.AsyncClient(headers=headers) as client:
            # Get data for the PoW
            r = await client.post(f"{base_url}/create_pow")
            if r.status_code != 200:
                raise PoWEndpointError(r.status_code, json_error(r))

            # Calculate PoW or ByPass
            pow_hardness = int(os.getenv("POW_HARDNESS", "21"))
            pow_data = r.json()
            target = powcheck.decrypt_and_validate(
                pow_data, bot_priv_key_b64, pow_hardness
            )

            # Simulate sleeping
            if simulsleep:
                await powcheck.delay_pow_response_async(target, True)

            # Buy a ticket with our proof of work
            r = await client.post(f"{base_url}/ticket", json={
                "pow-solution": target
            }, timeout=8.0)
            if r.status_code != 200:
                raise TicketCreationError(r.status_code, json_error(r))

            # If everything went fine we should get a ticket
            ticket = r.json()
            if "ticket" in ticket:
                return ticket["ticket"]

            raise TicketCreationError(500, "No ticket in JSON response")
    except httpx.TimeoutException:
        raise TicketCreationError(500, "Ticket creation timed out")
    except httpx.RequestError:
        raise TicketEndpointDown(500, "Ticket creation request failed")


async def order_items(base_url, ticket, flag):
    headers = {"user-agent": "python-requests/2.28.1"}

    try:
        async with httpx.AsyncClient(headers=headers) as client:
            # Get the list of available items
            r = await client.get(f"{base_url}/items")
            if r.status_code != 200:
                raise ItemEndpointError(r.status_code, json_error(r))

            # Gather all items
            items = []
            for category in r.json()['categories']:
                for item in category['items']:
                    items.append(item)

            # Random selection of items
            total = 0
            order_items = []
            while total < 14:
                item = random.choice(items)
                price = item['price']
                amount = random.randint(1, 2)
                total += amount * price
                order_items.append({
                    "id": item['item_id'],
                    "amount": amount
                })

            r = await client.post(
                f"{base_url}/order",
                json={
                    "order_items": order_items,
                    "table": random.randint(1, 42),
                    "notes": flag,
                    "ticket": ticket,
                },
                timeout=8.0
            )
            return r.json()
    except httpx.TimeoutException:
        raise ItemEndpointError(500, "Order requests timed out")
    except httpx.RequestError:
        raise OrderCreationError(500, "Error during order request")


async def place_order(base_url, flag, simulate):
    bot_privkey_bytes = os.environ.get(
        "POW_PRIVATE_KEY",
        "+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I=",
    )
    ticket = await get_ticket_async(base_url, bot_privkey_bytes)
    info = await order_items(base_url, ticket, flag)
    return info


async def send_handler(tc, send_queue):
    while msg := await send_queue.get():
        await tc.send(msg)


async def recv_handler(client, recv_handlers):
    while msg := await client.recv():
        if msg.msg_type == ToCanMsgType.CAN_FRAME:
            cmsg = msg.can_message
            mid = cmsg.arbitration_id
            if mid in recv_handlers:
                await recv_handlers[mid](cmsg)


async def query_order(host, gw_port, pos_url, order_info):
    bot_privkey_bytes = os.environ.get(
        "POW_PRIVATE_KEY",
        "+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I=",
    )
    ticket = await get_ticket_async(pos_url, bot_privkey_bytes)

    # Get config path
    config_path = Path(os.getenv("CONF_DIR", "/conf"))

    # Load message ID config
    config = dict()
    with open(config_path / "message-ids.yaml") as f:
        config = yaml.load(f.read(), yaml.CSafeLoader)

    toCanClient = ToCanClient(host, gw_port)
    connection = asyncio.create_task(toCanClient.connect())

    auth_key = base64.b64decode(order_info["auth_key"])
    cipher = cantina.Cipher()
    cipher.update(ChaCha20Poly1305(auth_key))

    send_queue = asyncio.Queue()
    order_client = cantina.canopy.Client(
        cipher,
        send_queue,
        {
            "canopy_start": config["MSGID_CLIENT_OPICKUP_START"],
            "canopy_data": config["MSGID_CLIENT_OPICKUP_DATA"],
            "canopy_reply_start": config[
                "MSGID_ODB_OPICKUP_REPLY_START"
            ],
            "canopy_reply_data": config["MSGID_ODB_OPICKUP_REPLY_DATA"],
        },
        #        logger=logger
    )

    recv_handlers = order_client.recv_handlers()

    async def workflow_handler(client, order_client):
        # Setup Filters
        filters = [
            (0x1FFFFFFF, config["MSGID_ODB_OPICKUP_REPLY_START"]),
            (0x1FFFFFFF, config["MSGID_ODB_OPICKUP_REPLY_DATA"]),
        ]
        filters = [(0, 0)]
        cfilt = CanFilter(filters)
        await client.send_msg(cfilt)

        ctok = CanToken(base64.b64decode(ticket))
        await client.send_msg(ctok)

        # TODO Randomize length of data
        reply = await order_client.send(
            b"Where is my order, Lebowsky?",
            Session(order_info["order_id"]),
        )

        # Check if we got any data
        if reply is None or reply[0] is None:
            raise OrderRetrievalError(500, f"Value of reply: {reply}")

        data = msgpack.unpackb(reply[0])
        return data

    sendh = asyncio.create_task(send_handler(toCanClient, send_queue))
    recvh = asyncio.create_task(
        recv_handler(toCanClient, recv_handlers)
    )
    workflow = asyncio.create_task(
        workflow_handler(toCanClient, order_client)
    )

    done, pending = await asyncio.wait(
        {connection, sendh, recvh, workflow},
        return_when=asyncio.FIRST_COMPLETED,
        timeout=8,
    )
    data = workflow.result()
    for task in done:
        task.result()
    for task in pending:
        task.cancel()
    return data


if __name__ == "__main__":

    base_url = "http://localhost:8080"
    info = asyncio.run(
        place_order(
            base_url, "FLG_YEEEEEEHAAAAAAAAAAAAAAAAAAAWWWWWWWWWW", False
        )
    )
    print("That's all, folks", info)

    info = asyncio.run(query_order("localhost", 9999, base_url, info))
    print("now really", info)
