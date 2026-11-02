"""Offline optimistic-concurrency protection for LiveSync updates."""
import base64
import hashlib
import unittest
from livesync_chunk_identity import legacy_chunk_id
from livesync_crypto import decrypt_hkdf_string
from livesync_isolated_update_plan import prepare_isolated_note_update
from livesync_write_preflight import UnsafeWrite
from livesync_revision_contract import RevisionConflict

PASS="disposable-only-passphrase"
SALT=base64.b64encode(b"disposable-ci-salt").decode()
REV="2-"+"a"*32
PATH="Tests/Example.md"
BEFORE="# Before\n"
AFTER="# After\n"
def parent():
    return {"_id":PATH.lower(),"path":PATH,"type":"plain",
            "_rev":REV,"children":["h:"+legacy_chunk_id(BEFORE,PASS)],
            "size":len(BEFORE.encode()),"ctime":1,"mtime":2,"eden":{}}
def build(**kwargs):
    return prepare_isolated_note_update(
        PATH, AFTER, kwargs.get("existing_parent",parent()),
        kwargs.get("current_content",BEFORE),
        kwargs.get("expected_revision",REV),
        kwargs.get("expected_content_sha256",hashlib.sha256(BEFORE.encode()).hexdigest()),
        PASS,SALT,modified_millis=3,
        remote_writes_enabled=kwargs.get("remote_writes_enabled",False))

class TestOfflineUpdate(unittest.TestCase):
    def test_builds_encrypted_leaf_and_cas_parent_without_mutation(self):
        original=parent()
        plan=build(existing_parent=original)
        self.assertEqual(plan["write_order"],("leaf","parent"))
        self.assertEqual(plan["expected_parent_revision"],REV)
        self.assertEqual(plan["parent"]["_rev"],REV)
        self.assertEqual(plan["parent"]["ctime"],1)
        self.assertEqual(plan["parent"]["children"],[plan["leaf"]["_id"]])
        self.assertEqual(decrypt_hkdf_string(plan["leaf"]["data"],PASS,SALT),AFTER)
        self.assertEqual(original["children"],["h:"+legacy_chunk_id(BEFORE,PASS)])
    def test_rejects_stale_revision_and_modified_content(self):
        with self.assertRaises(UnsafeWrite):
            build(expected_revision="3-"+"a"*32)
        with self.assertRaises(UnsafeWrite):
            build(current_content="modified elsewhere")
    def test_rejects_unverified_chunk_parent_and_remote_write(self):
        corrupted=parent()
        corrupted["children"]=["h:+wrong"]
        with self.assertRaises(UnsafeWrite):
            build(existing_parent=corrupted)
        with self.assertRaises(UnsafeWrite):
            build(remote_writes_enabled=True)
        with self.assertRaises(UnsafeWrite):
            build(current_content=BEFORE,expected_content_sha256="0"*64)
    def test_rejects_multichunk(self):
        corrupted=parent()
        corrupted["children"]*=2
        with self.assertRaises(UnsafeWrite):
            build(existing_parent=corrupted)

if __name__=="__main__":
    unittest.main()
