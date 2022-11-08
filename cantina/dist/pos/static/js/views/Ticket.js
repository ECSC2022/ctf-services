import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor() {
        super();
        this.setTitle("CANtina - Ticket");
    }

    async getHtml() {
        return `
            <main class="container">
            <h2>Tickets: Your Personal Credit Tokens</h2>
            <p>
            Tickets allow you to gain access to limited resources. You
            can generate these tickets here, by solving proof-of-work
            puzzles. We will use your PoW solutions to keep this place
            running and you can use them to order food from us. Use the
            following Python code for fetching/solving and sending a
            proof-of-work to us.
            </p>
            <code>
import requests
import hashlib
from base64 import b64decode

def calculate_pow(pow_message):
    pow_message['Salt'] = b64decode(pow_message['Salt'])
    salt_int = int.from_bytes(pow_message['Salt'], "big")
    for x in range(2**pow_message['Difficulty']):
        value = x + salt_int
        target = value.to_bytes(len(pow_message['Salt']), "big")
        hashed_candidate = hashlib.sha256(target).hexdigest()
        if pow_message['Hash'] == hashed_candidate:
            return x

def get_ticket(base_url) -> bytes:
    with requests.Session() as s:
        r = s.post(f'{base_url}/create_pow')
        pow_message = r.json()
        pow_solution = calculate_pow(pow_message)
        r = s.post(f'{base_url}/ticket', json={
            'pow-solution': pow_solution
        })
        return r.json()['ticket']

print(get_ticket('http://${window.location.host}'))
            </code>
            </main>
        `;
    }
}
