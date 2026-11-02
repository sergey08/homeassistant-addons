"""Read-only regression tests for encrypted LiveSync parent snapshots."""
import unittest
from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
from livesync_write_preflight import UnsafeWrite

REV = "2-" + "a" * 32

def stored():
    return {"_id":"f:encrypted-example","_rev":REV,"type":"plain",
            "path":"/\\:%=encrypted-metadata-placeholder"}

def decoded():
    return {"path":"Notes/Test.md","children":["h:+abc"],"size":10}

class EncryptedParentSnapshotTests(unittest.TestCase):
    def test_snapshot_preserves_opaque_identifiers(self):
        s=stored()
        result=validate_encrypted_parent_snapshot(s,decoded(),"Notes/Test.md",REV)
        self.assertEqual(result["_id"],s["_id"])
        self.assertEqual(result["_rev"],REV)
        self.assertEqual(result["encrypted_path"],s["path"])
        self.assertFalse(result["write_supported"])
        self.assertEqual(result["children"],("h:+abc",))

    def test_stale_revision_rejected(self):
        with self.assertRaises(UnsafeWrite):
            validate_encrypted_parent_snapshot(stored(),decoded(),"Notes/Test.md",
                                               "3-"+"b"*32)

    def test_invalid_path_metadata_rejected(self):
        with self.assertRaises(UnsafeWrite):
            validate_encrypted_parent_snapshot(stored(),decoded(),"Notes/Other.md",REV)

    def test_conflicts_and_plaintext_storage_rejected(self):
        for key,value in (("_conflicts",[REV]),("_deleted",True),
                          ("path","Notes/Test.md")):
            s=stored()
            s[key]=value
            with self.assertRaises(UnsafeWrite):
                validate_encrypted_parent_snapshot(s,decoded(),"Notes/Test.md",REV)

if __name__=="__main__":
    unittest.main()
