"""Offline fail-closed encrypted parent update contract; no network."""
import base64
import hashlib
import unittest
from livesync_encrypted_metadata_fixture import (
    encode_parent_metadata_fixture,decode_parent_metadata_fixture)
from livesync_obfuscated_parent_identity import legacy_obfuscated_parent_id
from livesync_obfuscated_update_plan import prepare_obfuscated_encrypted_update
from livesync_chunk_identity import legacy_chunk_id
from livesync_write_preflight import UnsafeWrite

PATH="Notes/Encrypted.md"
SECRET="disposable-fixture-only"
SALT=base64.b64encode(b"disposable-fixture-salt").decode()
REV="1-"+"a"*32
OLD="# Original\\n"
NEW="# Updated\\n"

def fixture():
    child="h:"+legacy_chunk_id(OLD,SECRET)
    meta=encode_parent_metadata_fixture(PATH,[child],SECRET,SALT,
        ctime=100,mtime=200,size=len(OLD.encode()))
    return {"_id":legacy_obfuscated_parent_id(PATH,SECRET),"_rev":REV,
        "type":"plain","eden":{},"path":meta["path"],
        "children":[],"ctime":0,"mtime":0,"size":0}

def prepare(parent=None,**kwargs):
    return prepare_obfuscated_encrypted_update(
        PATH,kwargs.pop("proposed_content",NEW),parent if parent is not None else fixture(),
        kwargs.pop("current_content",OLD),
        kwargs.pop("expected_revision",REV),
        kwargs.pop("expected_content_sha256",hashlib.sha256(OLD.encode()).hexdigest()),
        SECRET,SALT,modified_millis=kwargs.pop("modified_millis",300),**kwargs)

class TestOfflineObfuscatedUpdate(unittest.TestCase):
    def test_safe_plan_preserves_revision_and_encrypted_envelope(self):
        old=fixture()
        plan=prepare(old)
        self.assertEqual(plan["write_order"],("leaf","parent"))
        self.assertFalse(plan["write_supported"])
        self.assertEqual(old["children"],[])
        self.assertEqual(plan["parent"]["_rev"],REV)
        self.assertEqual(plan["parent"]["_id"],old["_id"])
        self.assertEqual(plan["parent"]["children"],[])
        self.assertNotEqual(plan["parent"]["path"],old["path"])
        self.assertEqual(plan["parent"]["eden"],{})
        decoded=decode_parent_metadata_fixture(plan["parent"]["path"],SECRET,SALT)
        self.assertEqual(decoded["path"],PATH)
        self.assertEqual(decoded["children"],[plan["leaf"]["_id"]])
        self.assertEqual(decoded["ctime"],100)
        self.assertEqual(decoded["mtime"],300)
        self.assertEqual(decoded["size"],len(NEW.encode()))
    def test_stale_revision_rejected(self):
        with self.assertRaises(UnsafeWrite):
            prepare(expected_revision="2-"+"b"*32)
    def test_changed_remote_content_rejected(self):
        with self.assertRaises(UnsafeWrite):
            prepare(current_content="# Different\\n")
    def test_mismatched_parent_id_rejected(self):
        p=fixture()
        p["_id"]="f:"+"0"*64
        with self.assertRaises(UnsafeWrite):
            prepare(p)
    def test_changed_or_multiple_children_rejected(self):
        p=fixture()
        alt=encode_parent_metadata_fixture(PATH,["h:+wrong"],SECRET,SALT,
            ctime=100,mtime=200,size=len(OLD.encode()))
        p["path"]=alt["path"]
        with self.assertRaises(UnsafeWrite):
            prepare(p)
    def test_malformed_update_inputs_rejected(self):
        for change in (
            {"current_content": ""},
            {"proposed_content": ""},
            {"proposed_content": "x" * 1001},
            {"current_content": "x" * 1001},
            {"modified_millis": -1},
            {"modified_millis": True},
            {"expected_content_sha256": "0" * 64},
            {"expected_content_sha256": "not-a-hash"},
        ):
            with self.subTest(change=change):
                with self.assertRaises(UnsafeWrite):
                    prepare(**change)

    def test_parent_deletion_and_invalid_metadata_rejected(self):
        for field, value in (
            ("_deleted", True),
            ("deleted", True),
            ("_conflicts", ["2-" + "b" * 32]),
            ("path", "not-encrypted"),
            ("_rev", "wrong-revision"),
        ):
            with self.subTest(field=field):
                parent = fixture()
                parent[field] = value
                with self.assertRaises(UnsafeWrite):
                    prepare(parent)

    def test_planning_does_not_mutate_existing_parent(self):
        parent = fixture()
        before = dict(parent)
        plan = prepare(parent)
        self.assertEqual(parent, before)
        self.assertIsNot(plan["parent"], parent)
        self.assertFalse(plan["write_supported"])

    def test_production_flag_rejected(self):
        with self.assertRaises(UnsafeWrite):
            prepare(remote_writes_enabled=True)
    def test_backdated_update_rejected(self):
        with self.assertRaises(UnsafeWrite):
            prepare(modified_millis=199)
    def test_keyed_identity_refused(self):
        with self.assertRaises(UnsafeWrite):
            prepare(id_derivation_key="not-supported")
    def test_conflicted_parent_rejected(self):
        p=fixture()
        p["_conflicts"]=["2-"+"a"*32]
        with self.assertRaises(UnsafeWrite):
            prepare(p)

if __name__=="__main__":
    unittest.main()
