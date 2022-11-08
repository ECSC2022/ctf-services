import base64
import json
import secrets
import sqlite3
import time
from pathlib import Path

import uvicorn
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Header, Request, Response
from pydantic import BaseModel
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes

app = FastAPI()

DB_LOCATION = "/data/user.db"
con = sqlite3.connect(DB_LOCATION)

enc_private_key = None
enc_public_key = None
sign_private_key = None
sign_public_key = None


class User(BaseModel):
    name: str
    token: str | None

def encrypt(privkey, b64pubkey, data):
    pubkey_bytes = base64.b64decode(b64pubkey)
    pubkey = x25519.X25519PublicKey.from_public_bytes(pubkey_bytes)
    cipher = ChaCha20Poly1305(HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'exch',
    ).derive(privkey.exchange(pubkey)))
    nonce = secrets.token_bytes(12)
    return base64.b64encode(nonce + cipher.encrypt(nonce, data, None))

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/user/authkey/{username}")
async def usertoken(
    username,
    response: Response,
    request: Request,
    key = Header(),
    authorization: str | None = Header(default=None),
):
    if authorization == None:
        return {"status": "ERR", "message": "Not authorized"}
    try:
        with con:
            cur = con.execute(
                f"SELECT authtoken FROM users where username='{username}'"
            )
            data = cur.fetchall()
            if data:
                msg = yaml.dump(list(data[0]), Dumper=yaml.Dumper)
                msg = encrypt(app.state.enc_key, key, msg.encode())
                return {
                    "status": "OK",
                    "message": msg,
                    "key": base64.b64encode(app.state.enc_key_pub_data).decode()
                }
            else:
                response.status_code = 404
                return {"status": "ERR", "message": "Not found"}

    except sqlite3.IntegrityError as e:
        return {"status": "ERR", "message": str(e)}, 500


@app.post("/user/create")
async def user_create(
    request: Request, key = Header(), authorization: str | None = Header(default=None)
):
    if authorization == None:
        return {"status": "ERR", "message": "Not authorized"}
    req = await request.body()
    user_info = yaml.load(req, Loader=yaml.Loader)
    if user := user_info.get("User"):
        if len(user) > 28:
            return {"status": "ERR", "message": "Username too long"}
        authtoken = secrets.token_hex(32)
        try:
            with con:
                cur = con.execute(
                    f"INSERT INTO users(username, authtoken) VALUES('{user}', '{authtoken}') RETURNING *"
                )
                msg = yaml.dump(list(cur.fetchall()[0]), Dumper=yaml.Dumper)
                msg = encrypt(app.state.enc_key, key, msg.encode())
                return {
                    "status": "OK",
                    "message": msg,
                    "key": base64.b64encode(app.state.enc_key_pub_data).decode()
                }
        except sqlite3.IntegrityError as e:
            return {"status": "ERR", "message": str(e)}

    return {"status": "ERR", "message": "No user info provided"}


@app.post("/jukebox/ticketrequest")
async def ticketrequest(
    request: Request, authenticateduser: str | None = Header(default=None)
):
    """Sign user requests for remote access to the jukebox"""

    if authenticateduser == None:
        return {"status": "ERR", "message": "Authorized"}

    req = await request.body()
    access_request = yaml.load(req, Loader=yaml.Loader)
    access_request["User"] = authenticateduser
    access_request["Ticket"] = dict(
        TicketId=secrets.token_urlsafe(4), Timestamp=int(time.time())
    )

    # access_request_data = yaml.dump(access_request,Dumper=yaml.Dumper).encode('ascii')
    access_request_data = json.dumps(access_request).encode("ascii")
    signature = app.state.sign_key.sign(access_request_data)
    # data = yaml.dump(access_request_data.encode('ascii'), Dumper=yaml.Dumper)
    return {
        "data": base64.b64encode(access_request_data),
        "signature": base64.b64encode(signature),
    }


@app.get("/publickey/sign")
async def get_signing_key():
    """Proxy request for authentication information"""
    return Response(
        content=base64.b64encode(app.state.sign_key_pub_data),
        media_type="application/octet-stream",
    )


@app.get("/publickey/encrypt")
async def get_encryption_key():
    """Proxy request for authentication information"""
    return Response(
        content=base64.b64encode(app.state.enc_key_pub_data),
        media_type="application/octet-stream",
    )


@app.get("/proxy/token/{username}")
async def proxy_auth_request(username, response: Response):
    """Proxy request for authentication information"""
    try:
        with con:
            cur = con.execute(
                f"SELECT authtoken FROM users where username='{username}'"
            )
            data = cur.fetchall()
            if data:
                userinfo = data[0]
                print(userinfo[0])
                return Response(
                    content=bytes(bytearray.fromhex(userinfo[0])),
                    media_type="application/octet-stream",
                )
            else:
                response.status_code = 404
                return {"status": "ERR", "message": "Not found"}

    except sqlite3.IntegrityError as e:
        return {"status": "ERR", "message": str(e)}, 500


@app.on_event("startup")
async def startup_event():

    sign_private_key_file = Path("/data/userdb_signing.pem")
    if sign_private_key_file.is_file():
        print("Signing key files already exist")
        sign_private_key = serialization.load_pem_private_key(
            sign_private_key_file.read_bytes(), None
        )
        sign_public_key = sign_private_key.public_key()
    else:
        print("Generate Signing Keys")
        sign_private_key = Ed25519PrivateKey.generate()
        sign_public_key = sign_private_key.public_key()

        sign_private_key_data = sign_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        sign_private_key_file.write_bytes(sign_private_key_data)

    app.state.sign_key = sign_private_key
    app.state.sign_key_pub = sign_public_key
    app.state.sign_key_pub_data = sign_public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    enc_private_key_file = Path("/data/userdb_encryption.pem")
    if enc_private_key_file.is_file():
        print("Key files already exist")
        enc_private_key = serialization.load_pem_private_key(
            enc_private_key_file.read_bytes(), None
        )
        enc_public_key = enc_private_key.public_key()
    else:
        print("Generating keypair")
        enc_private_key = x25519.X25519PrivateKey.generate()
        enc_public_key = enc_private_key.public_key()

        privkey_data = enc_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        enc_private_key_file.write_bytes(privkey_data)

    app.state.enc_key = enc_private_key
    app.state.enc_key_pub = enc_public_key
    app.state.enc_key_pub_data = enc_public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    with open("schema.sql") as f:
        con.executescript(f.read())
    con.commit()


if __name__ == "__main__":
    # uvicorn.run(app, uds="/data/userdb.sock", debug=True)
    uvicorn.run(app, port=10026, debug=True)
