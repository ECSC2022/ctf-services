import hashlib
import secrets
import time
import asyncio

import msgpack
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes, aead
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from base64 import b64decode as b64d


def calculate_pow(pow_message):
    pow_message['Salt'] = b64d(pow_message['Salt'])
    salt_int = int.from_bytes(pow_message['Salt'], "big")
    for x in range(2**pow_message['Difficulty']):
        value = x + salt_int
        target = value.to_bytes(len(pow_message['Salt']), "big")
        hashed_candidate = hashlib.sha256(target).hexdigest()
        if pow_message['Hash'] == hashed_candidate:
            return x


async def delay_pow_response_async(self, target, pow_delay=0):
    if pow_delay == True:
        hysteresis = secrets.randbelow(80)
        pow_delay = (430 + hysteresis) * 10e-10 * target
    print(pow_delay)
    await asyncio.sleep(pow_delay)



def delay_pow_response(self, target, pow_delay=0):
    if pow_delay == True:
        hysteresis = secrets.randbelow(80)
        pow_delay = (430 + hysteresis) * 10e-10 * target
    print(pow_delay)
    time.sleep(pow_delay)


def decrypt_and_validate(pow_message, bot_privkey_b64, expected_difficulty, pow_delay=None):
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=None,
    )
    session_pubkey = X25519PublicKey.from_public_bytes(
        b64d(pow_message['SessionPubKey'])
    )
    bot_privkey = X25519PrivateKey.from_private_bytes(
        b64d(bot_privkey_b64)
            )

    shared_key = bot_privkey.exchange(session_pubkey)
    derived_key = hkdf.derive(shared_key)

    cipher = b64d(pow_message['Ciphertext'])

    #nonce = cipher[:12]
    #ct = cipher[12:]

    chacha = aead.ChaCha20Poly1305(derived_key)
    plaintext = chacha.decrypt(b64d(pow_message['Nonce']), cipher, b'')
    hashed_enc = hashlib.sha256(plaintext).hexdigest()

    pow_message['Salt'] = b64d(pow_message['Salt'])
    target = int.from_bytes(plaintext, "big") ^ int.from_bytes(
       pow_message['Salt'], "big"
    )
    # Validate PoW
    if hashed_enc != pow_message['Hash']:
        raise PoWError("Hash mismatch")

    salt_int = int.from_bytes(plaintext, "big") & ~(
        pow(2, pow_message['Difficulty']) - 1
    )
    salt = salt_int.to_bytes(len(plaintext), "big")

    if not salt == pow_message['Salt']:
        raise PoWError("Salt mismatch (%s / %s)", pow_message['Salt'], salt)
    if target >= pow(2, expected_difficulty):
        raise PoWError(
            "Target and difficulty mismatch %d/%d", target, pow(2, expected_difficulty)
        )

    if pow_message['Difficulty'] > expected_difficulty:
        raise PoWError(
            "Difficulty mismatch %d/%d", pow_message['Difficulty'], expected_difficulty
        )

    if pow_delay != None:
        delay_pow_response(target, pow_delay)
    
    return target


def main():
    bot_privkey = X25519PrivateKey.generate()
    bot_pubkey = bot_privkey.public_key()

    bot_privkey_pem = bot_privkey.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    bot_pubkey_pem = bot_pubkey.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    pow_server = PoW(23, bot_pubkey=bot_pubkey_pem)
    pow_bot = PoW(
        23, bot_pubkey=bot_pubkey_pem, bot_privkey=bot_privkey_pem, pow_delay=True
    )
    pow_client = PoW()

    gen, target = pow_server.generate()
    print("Crack:", pow_bot.crack(gen))
    print("Crack2:", pow_client.crack(gen))


if __name__ == "__main__":

    data = {"Difficulty":21,"Hash":"f60bd4d54e5856f1fcadb6a71c409606eab52c042e332549ed4c8005c03e87e5","SessionPubKey":"LRq8Tuh1IEWcuVTg7Bq0cgamUnSACeUx9OAcrVWr6m0=","Ciphertext":"PahxyqiXKaXzemvzSrMJQuracW1xExe8dIFXu0zqI40=","Salt":"fYhF8dI0TFCqp+0po8AAAA==","Nonce":"+nt7pBKGe84weZsF"}
    data = {"Difficulty":21,"Hash":"52005dab249b0bf283544852211a1becb61374e0461f7a9f56f6029f287bc53e","SessionPubKey":"v4q/pLGqcAfj916XsOqI0Ow3imtnb8IGv1XsJ23W1CI=","Ciphertext":"YHhaSmL9HXP+3ZvWo9sRsiE3fPeus1BRTKWcP4xuNP0=","Salt":"TMrcqIVPJO44M966vuAAAA==","Nonce":"HY7/xCWQ9rWJbUst"} # Expected Target: 312233
    botPrivateKeyB64 = "+FhWjbCble523/+m/0VPVxMfxScN36+gYQM5aogpS3I="

    target = decrypt_and_validate(data, botPrivateKeyB64, 21)

    print(target)

    #main()
