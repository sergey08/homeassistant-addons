"""Read-only LiveSync HKDF (%=) string decoder.

Derived from the published LiveSync recovery format; supports %= only.
No IO, logging, persistent key storage, or fallback to unverified plaintext.
"""
import base64
import binascii
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

class UnsupportedEncryption(ValueError):
    pass

def decrypt_hkdf_string(value: str, passphrase: str, pbkdf2_salt_b64: str) -> str:
    if not isinstance(value, str) or not value.startswith("%="):
        raise UnsupportedEncryption("unsupported_ciphertext")
    if not isinstance(passphrase, str) or not passphrase:
        raise UnsupportedEncryption("missing_passphrase")
    try:
        salt = base64.b64decode(pbkdf2_salt_b64, validate=True)
        payload = base64.b64decode(value[2:], validate=True)
    except (TypeError, ValueError, binascii.Error):
        raise UnsupportedEncryption("invalid_encoding") from None
    if not salt or len(payload) < 60 or len(payload) > 2_000_000:
        raise UnsupportedEncryption("invalid_ciphertext_length")
    master = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 310_000, 32)
    iv, hkdf_salt, encrypted = payload[:12], payload[12:44], payload[44:]
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=hkdf_salt, info=b"").derive(master)
    try:
        plaintext = AESGCM(key).decrypt(iv, encrypted, None)
        return plaintext.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError):
        raise UnsupportedEncryption("decryption_failed") from None
