"""Synthetic HKDF LiveSync test vectors; no production secrets."""
import base64
import hashlib
import unittest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption

class TestHKDF(unittest.TestCase):
    def test_round_trip_and_wrong_passphrase(self):
        phrase = "synthetic test passphrase"
        salt = b"synthetic_pbkdf2_salt"
        iv = bytes(range(12))
        random_salt = bytes(range(32))
        master = hashlib.pbkdf2_hmac("sha256", phrase.encode(), salt, 310000, 32)
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=random_salt, info=b"").derive(master)
        ciphertext = AESGCM(key).encrypt(iv, "Demo/Prueba.md".encode(), None)
        value = "%=" + base64.b64encode(iv + random_salt + ciphertext).decode()
        encoded_salt = base64.b64encode(salt).decode()
        self.assertEqual(decrypt_hkdf_string(value, phrase, encoded_salt), "Demo/Prueba.md")
        with self.assertRaises(UnsupportedEncryption):
            decrypt_hkdf_string(value, "wrong passphrase", encoded_salt)

    def test_ephemeral_salt_format(self):
        phrase = "synthetic passphrase"
        salt = bytes(range(32))
        iv = bytes(range(12))
        hkdf_salt = bytes(range(32, 64))
        master = hashlib.pbkdf2_hmac("sha256", phrase.encode(), salt, 310000, 32)
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=hkdf_salt, info=b"").derive(master)
        encrypted = AESGCM(key).encrypt(iv, b"Demo/Encrypted.md", None)
        value = "%$" + base64.b64encode(salt + iv + hkdf_salt + encrypted).decode()
        self.assertEqual(decrypt_hkdf_string(value, phrase, ""), "Demo/Encrypted.md")
        with self.assertRaises(UnsupportedEncryption):
            decrypt_hkdf_string(value, "wrong", "")

    def test_invalid_ciphertext(self):
        with self.assertRaises(UnsupportedEncryption):
            decrypt_hkdf_string("%=not*base64", "pass", "c2FsdA==")
        with self.assertRaises(UnsupportedEncryption):
            decrypt_hkdf_string("plaintext", "pass", "c2FsdA==")

if __name__ == "__main__":
    unittest.main()
