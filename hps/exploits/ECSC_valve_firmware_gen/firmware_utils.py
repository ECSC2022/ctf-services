import hashlib

import tlv8
from Crypto.PublicKey import RSA


def generate_key():
    keyPair = RSA.generate(bits=2048)
    pubKey = keyPair.publickey()
    with open("private.pem", "w") as f:
        f.write(keyPair.exportKey("PEM").decode())
    with open("public.pem", "w") as f:
        f.write(pubKey.exportKey("PEM").decode())


def load_private_key():
    with open("private.pem", "r") as f:
        return RSA.importKey(f.read())


def load_public_key():
    with open("public.pem", "r") as f:
        return RSA.importKey(f.read())


def hash_sha512(data):
    return hashlib.sha512(data).digest()


def sign(my_hash):
    keyPair = load_private_key()
    return pow(int.from_bytes(my_hash, byteorder='big'), keyPair.d, keyPair.n)


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


def pack(extractor, data, inner_hash):
    result = []
    extractor_hash = hash_sha512(extractor)
    extractor_signature = sign(extractor_hash).to_bytes(length=2048, byteorder='big')
    result.append(tlv8.Entry(1, extractor_hash))
    result.append(tlv8.Entry(2, extractor_signature))
    result.append(tlv8.Entry(3, extractor))
    data_hash = hash_sha512(data)
    data_signature = sign(data_hash).to_bytes(length=2048, byteorder='big')
    result.append(tlv8.Entry(4, inner_hash))
    result.append(tlv8.Entry(5, data_signature))
    result.append(tlv8.Entry(6, data))
    return tlv8.encode(result)


def unpack(data):
    decoded = tlv8.decode(data, structure)
    extractor_hash = decoded[0].data
    extractor_signature = decoded[1].data
    if not verify(extractor_hash, int.from_bytes(extractor_signature, "big")):
        raise Exception("Signature is not valid")
    extractor = decoded[2].data
    return extractor


