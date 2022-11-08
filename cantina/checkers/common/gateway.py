from tocan import ToCanClient
from tocan.message import CanFilter, CanToken
from tocan.message import ToCanMsgType as tmType
import argtyper
from pathlib import Path
import asyncio
import can
import os
#import requests
import httpx
from powcheck import powcheck
import base64

@argtyper.Command(help="Run a ToCan Server")
async def server(host: str, port: int, can_interface: str, bot_pubkey_file: Path):
    bot_pubkey_pem = bot_pubkey_file.read_bytes()
    toCanServer = ToCanServer(host, port, can_interface, bot_pubkey_pem)
    await toCanServer.serve()


async def get_token(bot_priv_key_b64):
    async with httpx.AsyncClient() as client:
        r = await client.post('http://localhost:8080/create_pow')
        pow_data = r.json()

        print(pow_data) 
        target = powcheck.decrypt_and_validate(pow_data, bot_priv_key_b64, 21)
#        pow_data2 = pow_data.copy()
#        target2 = powcheck.calculate_pow(pow_data2)

        r = await client.post('http://localhost:8080/ticket', json={'pow-solution': target})
        ticket = r.json()['ticket']
        print(ticket)
        r = await client.post('http://localhost:8080/order', json={'order_items': [{ 'id': 0, 'amount': 1 }], 'table': 123, 'notes': 'test', 'ticket': ticket})
        print(r.json())
        return ticket



@argtyper.Command(
    help="Run a ToCan Client (optionally as bot when Private Key is passed)"
)
@argtyper.Argument("send", help="Send 'N' amount of test-messages to the server")
async def client(host: str, port: int, send: int = 0, bot_privkey_file: Path = None):

    bot_privkey_bytes = os.environ.get("POW_PRIVATE_KEY", '+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I=')
    ticket = await get_token(bot_privkey_bytes)

    toCanClient = ToCanClient(host, port)
    connection = asyncio.create_task(toCanClient.connect())


    async def logger(client):
        print("Logging Messages")
        while msg := await client.recv():

            print(msg)

            #print(f"Log: {msg}")

    async def send_msg(client, amount):

        ctok = CanToken(base64.b64decode(ticket))
        await client.send_msg(ctok)
    

        for x in range(amount):
            message = can.Message(
                arbitration_id=x + 100,
                data=f"HELLOWORLD: {x}".encode(),
                is_extended_id=True,
                is_fd=True,
            )
            await client.send(message)

        filters = [(0xFFFFFFFF,0x22200),(0,1),(0,2),(3,5)]
        cfilt = CanFilter(filters)
        await client.send_msg(cfilt)


    log = asyncio.create_task(logger(toCanClient))
    sender = asyncio.create_task(send_msg(toCanClient, send))
    done, pending = await asyncio.wait(
        {connection, log, sender}, return_when=asyncio.FIRST_EXCEPTION
    )
    for task in done:
        task.result()
    for task in pending:
        task.cancel()




@argtyper.SubCommand(client)
def main(debug: bool = False):

    if debug:
        import logging

        logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    arg = argtyper.ArgTyper(main)
    arg()
