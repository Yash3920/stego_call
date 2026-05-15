from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

SHARED_PASSWORD = "our_secret_pass_2024"
SALT = b'stegovoip_salt16'

def get_key() -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=480000)
    return kdf.derive(SHARED_PASSWORD.encode())

def encrypt(message: str) -> bytes:
    key = get_key()
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, message.encode('utf-8'), None)

def decrypt(payload: bytes) -> str:
    key = get_key()
    return AESGCM(key).decrypt(payload[:12], payload[12:], None).decode('utf-8')

def to_bits(data: bytes) -> list:
    return [int(b) for byte in data for b in f'{byte:08b}']

def from_bits(bits: list) -> bytes:
    return bytes(int(''.join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits) - 7, 8))