import base64
import json
import secrets
from functools import wraps
from pathlib import Path
from sqlite3.dbapi2 import IntegrityError
from typing import Dict, Optional
import time
import hashlib

import httpx
import uvicorn
import yaml
import aiosqlite
from starlette.applications import Starlette
from starlette.authentication import (AuthCredentials, AuthenticationBackend,
                                      AuthenticationError, SimpleUser)
from starlette.config import Config
from starlette.datastructures import FormData, Secret
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette_authlib.middleware import AuthlibMiddleware, SecretKey
import contextlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead \
    import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes


from vgm.instruction import VGM

import sqlite3


def respond_err(message):
    return {"message": message, "status": "ERR"}

def decrypt(privkey, b64pubkey, b64data):
    data = base64.b64decode(b64data)
    pubkey_bytes = base64.b64decode(b64pubkey)
    pubkey = x25519.X25519PublicKey.from_public_bytes(pubkey_bytes)
    cipher = ChaCha20Poly1305(HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'exch',
    ).derive(privkey.exchange(pubkey)))
    return cipher.decrypt(data[:12], data[12:], None)

class Proxy:
    def __init__(self, private_key, public_key):
        self.base_url = "http://localhost:10025"
        self.private_key = private_key
        self.key = base64.b64encode(public_key).decode()

    async def check_authtoken(self, username, authtoken):
        nested = {"Path": f"user/authkey/{username}", "Key": self.key}

        data = {"Data": json.dumps(nested)}
        async with httpx.AsyncClient() as c:
            resp = await c.post(f"{self.base_url}/proxy", json=data)
            data = resp.json()
            msg = json.loads(base64.b64decode(data["data"]))
            pt = decrypt(self.private_key, msg["key"], msg["message"])
            token = yaml.load(pt, Loader=yaml.Loader)[0]
            if token == authtoken:
                return True
        return False

    async def create_user(self, username, ticket):
        nested = {"Path": "user/create/", "Body": f'User: "{username}"', "Key": self.key}

        data = {"Data": json.dumps(nested)}
        async with httpx.AsyncClient() as c:
            data = await c.post(f"{self.base_url}/proxy", json=data)
            resp = data.json()
            if retval := resp.get("data", None):
                msg = yaml.load(base64.b64decode(retval), Loader=yaml.Loader)
                if msg.get("status", None) == "OK":
                    pt = decrypt(self.private_key, msg.get("key"), msg.get("message"))
                    user_info = yaml.load(pt, Loader=yaml.Loader)
                    return user_info
        return None

    async def verify_ticket(self, body):
        ticket = body.get("Ticket", None)
        if not ticket:
            return False, JSONResponse(respond_err("No Ticket provided"), 401)
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                f"{self.base_url}/ticket/validate", json={"Ticket": ticket}
            )
            data = resp.json()
            if err := data.get("error", None):
                return False, JSONResponse(respond_err(err), 401)
        return True, None



async def file_upload(request):
    if not request.session.get("User"):
        return JSONResponse(respond_err("Not logged in"), status_code=401)
    

    if request.method == "POST":
        user = request.session.get("User")
        form = await request.form()

        filename = form["file"].filename
        fname = Path(filename)
        if fname.suffix not in [".vgm",".vgz"]:
            return JSONResponse(respond_err('Unknown file extension'), 400)
        contents = await form["file"].read()
        if len(contents) > 2**18:
            return JSONResponse(respond_err('File too large'), 413)

        vgm = VGM()
        vgm.parse_memory(contents, fname.suffix)
        verified = vgm.verify()

        if not verified:
            return JSONResponse(respond_err('File verification failed'), 400)
 
        file_info = vgm.parsed_info()
        filename = Path( str(int(time.time())) + '_' +hashlib.sha256(vgm.data).hexdigest()[0:12] + '.vgm')
        filedir = request.app.state.UPLOAD_DIR / user 
        filedir.mkdir(parents=True, exist_ok=True)
        filepath = filedir / filename
        if filepath.exists():
            return JSONResponse(respond_err('File exists'), 409)
            
        with filepath.open('wb') as output:
            output.write(vgm.data)
        
        try:
            cur =await app.state.conn.execute(
                    f"INSERT INTO files(username, track, game, author, filename) VALUES(?,?,?,?,?) RETURNING *",
                    (user, file_info['track'] , 
                           file_info['game']  ,
                           file_info['author'],
                     str(filename))
                )
            data = await cur.fetchall()
            await app.state.conn.commit()
            return JSONResponse(dict(filename=str(filename), file_info=data[0][:-1]))
        except sqlite3.IntegrityError as e:
            if not request.session.get("User"):
                return JSONResponse(respond_err("Server Error"), status_code=500)


async def file_info(request):
    user = request.session.get("User")
    filename = request.path_params.get('File','')
    username = request.query_params.get('User')

    base = user
    if username:
        base=username
        query_self = False
    else:
        query_self = True

    if not base:
        return JSONResponse(respond_err('No such file'), 404)

    filepath = None
    try:
        filedir = request.app.state.UPLOAD_DIR / base
        filedir.relative_to(request.app.state.UPLOAD_DIR)
        filepath = filedir / filename
        filepath.relative_to(filedir)
    except ValueError as e:
        return JSONResponse(respond_err('No such file'), 404)
   
    if not filepath or not filepath.exists():
        return JSONResponse(respond_err('No such file'), 404)

    vgm = VGM()
    vgm.parse_file(filepath)
    info = vgm.parsed_info()
    if not query_self:
        info['notes'] = f'Brought to you by {base}'
    return JSONResponse(info)


async def file_list(request):
    user = request.session.get("User")
    if not user:
        return JSONResponse(respond_err("Not logged in."), status_code=403)

    try:
        from_id = request.query_params.get('from')
        if from_id:
            cur = await app.state.conn.execute(
                    f"SELECT * FROM files where id >= ? order by id asc limit 20",
                    (from_id,)
                )
        else:
            cur = await app.state.conn.execute(
                    f"SELECT * FROM files order by id desc limit 20" 
                )
        data = await cur.fetchall()
        await app.state.conn.commit()
        return JSONResponse(data)
    except sqlite3.IntegrityError as e:
        if not request.session.get("User"):
            return JSONResponse(respond_err("Server Error"), status_code=500)
       


async def login(request):
    """
    A login endpoint that creates a session.
    """
    if request.method == "POST":
        user = request.session.get("User")
        if user:
            return JSONResponse({
                "message": "Already authorized",
                "username": user
            }, 200)

        if "json" in request.headers.get('content-type').lower():
            body = await request.json()
        else:
            body = await request.form()

        username = body.get("User", None)
        authtoken = body.get("Token", None)
        if not username or not authtoken:
            return JSONResponse(respond_err("Invalid Credentials"), 401)
        if not (username.isalnum() and authtoken.isalnum()):
            return JSONResponse(respond_err("Invalid Credentials"), 401)
        ticket = body.get("Ticket")
        if not ticket:
            JSONResponse(respond_err("Need a ticket. Get one at the PoS terminal"), 401)

        prox = Proxy(request.app.state.PRIVATE_KEY, request.app.state.PUBLIC_KEY)
        valid, err = await prox.verify_ticket(body)
        if err:
            return err

        data = await prox.check_authtoken(username, authtoken)
        if data:
            request.session.update(
                {
                    "iss": "jukebox",
                    "User": username,
                }
            )
            return JSONResponse({}, 200)
        return JSONResponse({"message": "Not authorized"}, 401)


async def register(request):
    body = await request.json()
    username = body.get("User", None)
    if not username:
        return JSONResponse(respond_err("Invalid Username"), 400)
    if not (username.isalnum() and len(username) > 8 and len(username) <= 28):
        return JSONResponse(
            respond_err(
                "Username must be alphanumeric, and between 8 and 28 characters"
            ),
            400,
        )

    username = body.get("User", None)

    ticket = body.get("Ticket")
    if not ticket:
        JSONResponse(respond_err("Need a ticket. Get one at the PoS terminal"), 401)
    prox = Proxy(request.app.state.PRIVATE_KEY, request.app.state.PUBLIC_KEY)
    valid, err = await prox.verify_ticket(body)
    if err:
        return err
    data = await prox.create_user(username, ticket)
    if not data:
        JSONResponse(respond_err("User creation failed"), 400)

    return JSONResponse(data, 201)


@contextlib.asynccontextmanager
async def lifespan(app):
    app.state.PRIVATE_KEY = x25519.X25519PrivateKey.generate()
    app.state.PUBLIC_KEY = app.state.PRIVATE_KEY.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    async with aiosqlite.connect(app.state.DB_LOCATION) as app.state.conn:
        with open("schema.sql") as f:
            await app.state.conn.executescript(f.read())
            await app.state.conn.commit()
        print("Ready to Rock!")
        yield


async def handle_error(request: Request, exc: HTTPException):
    # Perform some logic
    return JSONResponse({"message": exc.detail}, status_code=exc.status_code)

config = Config("/data/.env")

secret_key = config(  # pylint: disable=invalid-name
    "JWT_SECRET", cast=Secret, default=secrets.token_hex(32)
)

with open('/data/.env', 'w') as env:
    env.write(f'JWT_SECRET={secret_key}')

static_dir=config("STATIC_DIR", cast=Path, default=Path("/app/static"))

async def handle_404(_: Request, __: HTTPException):
    return FileResponse(static_dir / 'index.html')

exception_handlers = {
        Exception: handle_error,
        404: handle_404
}  # or "500: handle_error"

app = Starlette(
    debug=True,
    lifespan=lifespan,
    exception_handlers=exception_handlers,
    routes=[
        Route("/login", endpoint=login, methods=["GET", "POST"]),
        Route("/file/upload", endpoint=file_upload, methods=["GET", "POST"]),
        Route("/file/list/",  endpoint=file_list, methods=["GET"]),
        Route("/file/list/{User}",  endpoint=file_list, methods=["GET"]),
        Route("/file/info/{File}",  endpoint=file_info, methods=["GET"]),
        Route("/register", endpoint=register, methods=["POST"]),
        Mount("/", app=StaticFiles(directory=static_dir, html=True), name="static"),
    ],
    middleware=[
        Middleware(AuthlibMiddleware, secret_key=secret_key),
    ],
)

app.state.DATA_DIR = config("DATA_DIR", cast=Path, default="/data")
app.state.UPLOAD_DIR = Path(app.state.DATA_DIR) / "uploads"
app.state.DB_LOCATION = "/data/user.db"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10024, log_level="debug")
