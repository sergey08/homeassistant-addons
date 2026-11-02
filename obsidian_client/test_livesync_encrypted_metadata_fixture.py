"""Offline encryption metadata fixture: structure and fail-closed behavior."""
import base64
import unittest
from livesync_encrypted_metadata_fixture import (
    encode_parent_metadata_fixture,decode_parent_metadata_fixture)
from livesync_write_preflight import UnsafeWrite

SALT=base64.b64encode(b"disposable-fixture-salt").decode()

class TestEncryptedMetadataFixture(unittest.TestCase):
    def test_round_trip_and_zeroed_outer_fields(self):
        result=encode_parent_metadata_fixture(
            "Notes/Example.md",["h:+abc"],"disposable-fixture-passphrase",
            SALT,ctime=100,mtime=200,size=17)
        self.assertTrue(result["path"].startswith("/\\:%="))
        self.assertEqual(result["children"],[])
        self.assertEqual((result["mtime"],result["ctime"],result["size"]),(0,0,0))
        self.assertFalse(result["write_supported"])
        decoded=decode_parent_metadata_fixture(result["path"],
            "disposable-fixture-passphrase",SALT)
        self.assertEqual(decoded,{"path":"Notes/Example.md","mtime":200,
                                  "ctime":100,"size":17,"children":["h:+abc"]})
    def test_encrypted_metadata_uses_random_nonce(self):
        args=("Notes/Example.md",["h:+abc"],"disposable-fixture-passphrase",SALT)
        a=encode_parent_metadata_fixture(*args,ctime=1,mtime=2,size=3)
        b=encode_parent_metadata_fixture(*args,ctime=1,mtime=2,size=3)
        self.assertNotEqual(a["path"],b["path"])
    def test_fail_closed_invalid_inputs(self):
        with self.assertRaises(UnsafeWrite):
            encode_parent_metadata_fixture("../bad.md",["h:+abc"],
                "disposable-fixture-passphrase",SALT,ctime=1,mtime=2,size=3)
        with self.assertRaises(UnsafeWrite):
            encode_parent_metadata_fixture("Note.md",["arbitrary"],
                "disposable-fixture-passphrase",SALT,ctime=1,mtime=2,size=3)
        with self.assertRaises(UnsafeWrite):
            encode_parent_metadata_fixture("Note.md",["h:+abc"],
                "disposable-fixture-passphrase",SALT,ctime=True,mtime=2,size=3)

if __name__=="__main__":
    unittest.main()
