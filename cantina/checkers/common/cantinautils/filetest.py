import httpx
import asyncio
import base64
import json
import secrets
import yaml




base_url = "http://localhost:8080"


async def get_ticket_async(
    base_url, bot_priv_key_b64, simulsleep=False
):
    # TODO: Random user agent
    headers = {"user-agent": "python-requests/2.28.1"}

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
        })
        if r.status_code != 200:
            raise TicketCreationError(r.status_code, json_error(r))

        # If everything went fine we should get a ticket
        ticket = r.json()
        if "ticket" in ticket:
            return ticket["ticket"]

        raise TicketCreationError(500, "No ticket in JSON response")





async def create_user(base_url, username):



    async with httpx.AsyncClient() as c:
        username = secrets.token_hex(14)
        nested = {'Path': "user/create/",
                  'Body': f'User: "{username}"\nuser: test'}

        data = {'Data': json.dumps(nested)}
        data = await c.post(f'{base_url}/proxy', json=data)
        resp = data.json()
        if retval := resp.get('data', None):
            msg = yaml.load(base64.b64decode(retval),Loader=yaml.Loader)
            if msg.get("status", None) == 'OK':
                user_info = yaml.load(msg.get('message'),Loader=yaml.Loader)
                return user_info
        return resp
        print(resp)


async def run_test():

    tasks = []
    for x in range(100):
        task = asyncio.create_task( create_user(base_url, "neo"))
        tasks.append(task)
    done, pending = await asyncio.wait( tasks )
    for task in done:
        print(task.result())

if __name__ == "__main__":

    info = asyncio.run(run_test())
#    print("That's all, folks", info)
#
#    info = asyncio.run(query_order("localhost", 9999, base_url, info))
#    print("now really", info)

