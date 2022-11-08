import hashlib
import subprocess

import tlv8
from Crypto.PublicKey import RSA


def chroot_cp(file, dest):
    directory = dest[:dest.rindex("/")] + "/"
    subprocess.check_output(["mkdir", "-p", directory])
    subprocess.check_output(["cp", "-R", file, dest])


def load_public_key():
    with open("public.pem", "r") as f:
        return RSA.importKey(f.read())


def hash_sha512(data):
    return hashlib.sha512(data).digest()


def verify(my_hash, signature):
    pubKey = load_public_key()
    return pow(signature, pubKey.e, pubKey.n) == int.from_bytes(my_hash, byteorder='big')


structure = {
        1: tlv8.DataType.BYTES, # hash
        2: tlv8.DataType.BYTES, # signature
        3: tlv8.DataType.BYTES, # extractor
        4: tlv8.DataType.BYTES, # data_hash
        5: tlv8.DataType.BYTES, # data_signature
        6: tlv8.DataType.BYTES, # data
    }


def unpack(data):
    decoded = tlv8.decode(data, structure)
    extractor_hash = decoded[0].data
    extractor_signature = decoded[1].data
    if not verify(extractor_hash, int.from_bytes(extractor_signature, "big")):
        raise Exception("Signature is not valid")
    extractor = decoded[2].data
    data_hash = decoded[3].data
    data_signature = decoded[4].data
    data = decoded[5].data
    return extractor, data, data_hash, data_signature


