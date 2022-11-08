from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519

from pathlib import Path

def generate_bot_keys(replace_files=False):

    bot_key_private = x25519.X25519PrivateKey.generate()
    bot_key_public = bot_key_private.public_key()
 
    privkey_data = bot_key_private.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                )

    pubkey_data = bot_key_public.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                )

    
#    private_key_file = Path("bot_key_private.pem")
#    if private_key_file.is_file() and not replace_files:
#        print("Key files already exist")
#        return
#    private_key_file.write_bytes(privkey_data)
#    public_key_file = Path("bot_key_public.pem")
#    public_key_file.write_bytes(pubkey_data)
    print(privkey_data)
    print(pubkey_data)

    
    privkey_data = bot_key_private.private_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PrivateFormat.Raw,
                        encryption_algorithm=serialization.NoEncryption()
                )

    pubkey_data = bot_key_public.public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw
                )

    import base64
    print("Priv:", base64.b64encode(privkey_data))
    print("Pub:", base64.b64encode(pubkey_data))


if __name__ == "__main__":
    generate_bot_keys()
