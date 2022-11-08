from cantina.powcheck import powcheck
from cantina.tocan import ToCanClient
from cantina.tocan.message import *
import cantina
from cantina.canopy.fields import Session
import httpx
import asyncio
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import base64
import yaml
import json


class CantinaError(Exception):
    pass


class TicketCreationError(CantinaError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'{self.status}: {self.message}')


def json_error(r):
    try:
        return r.json()['error']
    except json.JSONDecodeError:
        return r.text


async def get_ticket_async(
    base_url, bot_priv_key_b64, simulsleep=False
):
    headers = {"user-agent": "python-requests/2.28.1"}
    async with httpx.AsyncClient(headers=headers) as client:
        r = await client.post(f"{base_url}/create_pow")
        pow_data = r.json()
        target = powcheck.decrypt_and_validate(
            pow_data, bot_priv_key_b64, 21
        )
        if simulsleep:
            await powcheck.delay_pow_response_async(target, True)

        # Buy a ticket with our proof of work
        r = await client.post(f"{base_url}/ticket", json={
            "pow-solution": target
        })
        if r.status_code != 200:
            raise TicketCreationError(r.status_code, json_error(r))

        # If everything went fine we should get a ticket
        ticket = r.json()["ticket"]
        return ticket


async def order_items(base_url, ticket, flag):
    ##################################
    # TODO Randomize orders
    #################################
    headers = {"user-agent": "python-requests/2.28.1"}
    async with httpx.AsyncClient(headers=headers) as client:
        r = await client.post(
            f"{base_url}/order",
            json={
                "order_items": [{"id": 0, "amount": 1}],
                "table": 123,
                "notes": flag,
                "ticket": ticket,
            },
        )
        return r.json()


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
        timeout=5,
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

