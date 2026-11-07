"""Real CouchDB integration / Integración real con CouchDB.

Runs ONLY when TEST_COUCHDB_URL is set. Creates and deletes a uniquely
named disposable database on the test server. Never use production credentials.
"""
import base64
import json
import os
import unittest
import uuid
from unittest.mock import patch
from server import app
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from livesync_plain import decode_plain_note


@unittest.skipUnless(os.environ.get("TEST_COUCHDB_URL"), "Isolated CouchDB not configured")
class RealCouchDBIntegrationTests(unittest.TestCase):
    def test_disposable_database_roundtrip(self):
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        if root not in ("http://127.0.0.1:5984", "http://localhost:5984"):
            self.fail("Safety: disposable test database only permitted on loopback CouchDB:5984")
        username = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        if not username or not password:
            self.fail("Safety: test-only admin credentials required")
        auth = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        db = "obsidian_ci_" + uuid.uuid4().hex
        base = root + "/" + db
        def call(url, method="GET", payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            req = Request(url, data=body, method=method,
                          headers={"Authorization": auth, "Content-Type": "application/json"})
            with urlopen(req, timeout=8) as resp:
                return json.load(resp)

        created = False
        try:
            result = call(base, "PUT")
            self.assertTrue(result.get("ok"))
            created = True
            config = {
                "livesync_cli_enabled": True,
                "couchdb_url": root,
                "couchdb_database": db,
                "couchdb_username": username,
                "couchdb_password": password,
                "livesync_encryption_enabled": True,
                "livesync_e2ee_passphrase": "isolated-ci-only",
            }
            with patch("server.options", return_value=config):
                response = app.test_client().get("/api/livesync-cli/connection-check")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["status"], "database_reachable")
            self.assertFalse(response.json["encryption_verified"])
            self.assertFalse(response.json["remote_writes_enabled"])
            config["couchdb_password"] = "incorrect-test-password"
            with patch("server.options", return_value=config):
                rejected = app.test_client().get("/api/livesync-cli/connection-check")
            self.assertEqual(rejected.status_code, 502)
            self.assertEqual(rejected.json["status"], "authentication_failed")
            parent = {"_id": "f:synthetic", "type": "plain", "path": "Tests/Hello.md",
                      "children": ["h:first", "h:second"], "size": 11}
            chunks = [
                {"_id": "h:first", "type": "leaf", "data": "Hello "},
                {"_id": "h:second", "type": "leaf", "data": "world"},
            ]
            for doc in [parent] + chunks:
                self.assertTrue(call(base + "/" + quote(doc["_id"], safe=""), "PUT", doc).get("ok"))
            rows = call(base + "/_all_docs?include_docs=true")["rows"]
            docs = {row["id"]: row["doc"] for row in rows}
            self.assertEqual(decode_plain_note(docs["f:synthetic"], docs),
                             {"path": "Tests/Hello.md", "content": "Hello world"})
        finally:
            if created:
                self.assertTrue(call(base, "DELETE").get("ok"))


    def test_disposable_revision_conflict(self):
        """CouchDB must atomically reject a stale revision without losing a write."""
        from livesync_revision_contract import (
            RevisionConflict, prepare_conditional_document, require_successful_put,
        )
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        self.assertIn(root, ("http://127.0.0.1:5984", "http://localhost:5984"))
        username = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        self.assertTrue(username and password)
        auth = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        base = root + "/obsidian_cas_ci_" + uuid.uuid4().hex

        def call(url, method="GET", payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            req = Request(url, data=body, method=method,
                          headers={"Authorization": auth, "Content-Type": "application/json"})
            with urlopen(req, timeout=8) as response:
                return response.status, json.load(response)

        created = False
        try:
            self.assertEqual(call(base, "PUT")[0], 201)
            created = True
            doc_url = base + "/synthetic-note"
            initial = {"_id": "synthetic-note", "type": "plain", "data": "initial"}
            status, inserted = call(doc_url, "PUT", initial)
            self.assertTrue(require_successful_put(status, inserted))
            _, old = call(doc_url)
            rev = old["_rev"]
            first = prepare_conditional_document(
                old, {**old, "data": "first-writer"}, rev)
            status, saved = call(doc_url, "PUT", first)
            self.assertTrue(require_successful_put(status, saved))
            stale = prepare_conditional_document(
                old, {**old, "data": "stale-writer"}, rev)
            with self.assertRaises(HTTPError) as rejected:
                call(doc_url, "PUT", stale)
            self.assertEqual(rejected.exception.code, 409)
            with self.assertRaisesRegex(RevisionConflict, "remote_revision_conflict"):
                require_successful_put(409, {"error": "conflict"})
            _, latest = call(doc_url)
            self.assertEqual(latest["data"], "first-writer")
            self.assertEqual(latest["_rev"], saved["rev"])
        finally:
            if created:
                self.assertEqual(call(base, "DELETE")[0], 200)


    def test_encrypted_metadata_and_leaf_roundtrip_disposable(self):
        """Synthetic encrypted parent and leaf; no production writes."""
        from livesync_crypto import encrypt_hkdf_string, decrypt_hkdf_string
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        self.assertIn(root, ("http://127.0.0.1:5984", "http://localhost:5984"))
        user = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        self.assertTrue(user and password)
        auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        db = root + "/obsidian_encrypted_docs_ci_" + uuid.uuid4().hex

        def call(url, method="GET", payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            req = Request(url, data=body, method=method,
                          headers={"Authorization": auth, "Content-Type": "application/json"})
            with urlopen(req, timeout=8) as resp:
                return resp.status, json.load(resp)

        phrase = "isolated-only-secret"
        salt = base64.b64encode(b"synthetic-remote-pbkdf2-salt").decode()
        markdown = "# Encrypted test\\nTexto de prueba 🌍\\n"
        doc_id = "synthetic-parent"
        leaf_id = "synthetic-leaf"
        meta = {"path": "Tests/encrypted.md", "children": [leaf_id],
                "size": len(markdown.encode("utf-8"))}
        parent = {"_id": doc_id, "type": "plain",
                  "path": "/\\:%=" + encrypt_hkdf_string(json.dumps(meta), phrase, salt)[2:],
                  "children": [leaf_id], "size": meta["size"]}
        leaf = {"_id": leaf_id, "type": "leaf",
                "data": encrypt_hkdf_string(markdown, phrase, salt)}
        created = False
        try:
            self.assertEqual(call(db, "PUT")[0], 201)
            created = True
            self.assertEqual(call(db + "/" + doc_id, "PUT", parent)[0], 201)
            self.assertEqual(call(db + "/" + leaf_id, "PUT", leaf)[0], 201)
            _, read_parent = call(db + "/" + doc_id)
            _, read_leaf = call(db + "/" + leaf_id)
            decoded_meta = json.loads(decrypt_hkdf_string(
                read_parent["path"][3:], phrase, salt))
            decoded_markdown = decrypt_hkdf_string(read_leaf["data"], phrase, salt)
            self.assertEqual(decoded_meta, meta)
            self.assertEqual(decoded_markdown, markdown)
            self.assertEqual(len(decoded_markdown.encode("utf-8")), decoded_meta["size"])
        finally:
            if created:
                self.assertEqual(call(db, "DELETE")[0], 200)


    def test_disposable_encrypted_leaf_and_parent_cas_rejects_stale_writer(self):
        """Only loopback disposable DB; encrypted parent is updated with _rev CAS."""
        from livesync_crypto import encrypt_hkdf_string, decrypt_hkdf_string
        from livesync_encrypted_metadata_fixture import (
            encode_parent_metadata_fixture, decode_parent_metadata_fixture)
        from livesync_revision_contract import (
            prepare_conditional_document, RevisionConflict)
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        self.assertIn(root, ("http://127.0.0.1:5984", "http://localhost:5984"))
        user = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        self.assertTrue(user and password)
        auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        base = root + "/obsidian_encrypted_cas_ci_" + uuid.uuid4().hex
        salt = base64.b64encode(b"disposable-ci-encrypted-cas-salt").decode()
        phrase = "disposable-ci-only"
        path = "Disposable/Encrypted.md"
        original = "# Primera revision\\n"
        updated = "# Segunda revision\\n"
        parent_id, old_leaf_id, new_leaf_id = (
            "test:encrypted-parent", "h:+testencryptedold", "h:+testencryptednew")

        def call(url, method="GET", payload=None, headers=None):
            wire = json.dumps(payload).encode("utf-8") if payload is not None else None
            request = Request(url, data=wire, method=method, headers={
                "Authorization": auth, "Content-Type": "application/json",
                **(headers or {})})
            with urlopen(request, timeout=8) as response:
                return response.status, json.load(response)

        created = False
        try:
            self.assertEqual(call(base, "PUT")[0], 201)
            created = True
            parent_meta = encode_parent_metadata_fixture(
                path, [old_leaf_id], phrase, salt,
                ctime=1730000000000, mtime=1730000000000,
                size=len(original.encode("utf-8")))
            parent = {
                "_id": parent_id, "type": "plain",
                "path": parent_meta["path"], "children": [],
                "ctime": 0, "mtime": 0, "size": 0, "eden": {}}
            old_leaf = {
                "_id": old_leaf_id, "type": "leaf", "e_": True,
                "data": encrypt_hkdf_string(original, phrase, salt)}
            self.assertEqual(call(base + "/" + parent_id, "PUT", parent)[0], 201)
            self.assertEqual(call(base + "/" + old_leaf_id, "PUT", old_leaf)[0], 201)
            _, stored_parent = call(base + "/" + parent_id)
            old_rev = stored_parent["_rev"]

            new_leaf = {
                "_id": new_leaf_id, "type": "leaf", "e_": True,
                "data": encrypt_hkdf_string(updated, phrase, salt)}
            self.assertEqual(call(base + "/" + new_leaf_id, "PUT", new_leaf)[0], 201)
            next_meta = encode_parent_metadata_fixture(
                path, [new_leaf_id], phrase, salt,
                ctime=1730000000000, mtime=1730000001000,
                size=len(updated.encode("utf-8")))
            proposed = prepare_conditional_document(
                stored_parent,
                {**stored_parent, "path": next_meta["path"]}, old_rev)
            endpoint = base + "/" + parent_id
            request_headers = {"If-Match": '"' + old_rev + '"'}
            status, saved = call(endpoint, "PUT", proposed, request_headers)
            self.assertEqual(status, 201)
            self.assertTrue(saved["ok"])

            with self.assertRaises(HTTPError) as stale:
                call(endpoint, "PUT", proposed, request_headers)
            self.assertIn(stale.exception.code, (409, 412))
            _, current_parent = call(endpoint)
            self.assertEqual(current_parent["_rev"], saved["rev"])
            decoded_meta = decode_parent_metadata_fixture(
                current_parent["path"], phrase, salt)
            self.assertEqual(decoded_meta["children"], [new_leaf_id])
            _, current_leaf = call(base + "/" + new_leaf_id)
            self.assertEqual(
                decrypt_hkdf_string(current_leaf["data"], phrase, salt), updated)
            _, old_leaf_still_exists = call(base + "/" + old_leaf_id)
            self.assertEqual(
                decrypt_hkdf_string(old_leaf_still_exists["data"], phrase, salt),
                original)
        finally:
            if created:
                self.assertEqual(call(base, "DELETE")[0], 200)


    def test_multichunk_readback_then_parent_cas_in_disposable_database(self):
        """All encrypted leaves must be readable before existing parent CAS."""
        from livesync_crypto import encrypt_hkdf_string
        from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
        from livesync_isolated_multichunk_commit import commit_isolated_multichunk_plan
        from livesync_multichunk_audit import assemble_encrypted_chunks
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        self.assertIn(root, ("http://127.0.0.1:5984", "http://localhost:5984"))
        user = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        self.assertTrue(user and password)
        auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        base = root + "/obsidian_multichunk_cas_ci_" + uuid.uuid4().hex
        phrase = "isolated-ci-multichunk"
        salt = base64.b64encode(b"isolated-ci-multichunk-salt").decode()
        note_path = "Tests/Multi.md"
        parent_id = "synthetic-parent"
        parts = ("Hola ", "mundo 🌍", "\\n")
        ids = ["h:+disposable" + str(i) for i in range(len(parts))]

        def call(doc_id=None, method="GET", payload=None):
            url = base + ("/" + quote(doc_id, safe="") if doc_id is not None else "")
            request = Request(url, method=method,
                data=json.dumps(payload).encode("utf-8") if payload is not None else None,
                headers={"Authorization": auth, "Content-Type": "application/json"})
            with urlopen(request, timeout=8) as response:
                return response.status, json.load(response)

        created = False
        try:
            self.assertEqual(call(method="PUT")[0], 201)
            created = True
            original_meta = encode_parent_metadata_fixture(
                note_path, ["h:+prior"], phrase, salt,
                ctime=100, mtime=100, size=5)
            original = {"_id": parent_id, "type": "plain",
                        "path": original_meta["path"], "children": [],
                        "ctime": 0, "mtime": 0, "size": 0}
            self.assertEqual(call(parent_id, "PUT", original)[0], 201)
            _, stored = call(parent_id)
            meta = encode_parent_metadata_fixture(
                note_path, ids, phrase, salt, ctime=100, mtime=200,
                size=len("".join(parts).encode("utf-8")))
            leaves = [
                {"_id": ident, "type": "leaf", "e_": True,
                 "data": encrypt_hkdf_string(part, phrase, salt)}
                for ident, part in zip(ids, parts)]
            parent = {**stored, "path": meta["path"], "children": [],
                      "ctime": 0, "mtime": 0, "size": 0}
            plan = {"write_supported": False, "path": note_path,
                    "leaves": leaves, "parent": parent,
                    "expected_parent_revision": stored["_rev"]}
            sequence = []

            def put(doc):
                sequence.append(("put", doc["_id"]))
                try:
                    return call(doc["_id"], "PUT", doc)
                except HTTPError as exc:
                    return exc.code, {"error": "conflict"}

            def read(doc_id):
                sequence.append(("get", doc_id))
                return call(doc_id)[1]

            committed = commit_isolated_multichunk_plan(
                plan, put, read, phrase, salt, isolated_test=True)
            self.assertEqual(committed["confirmed_chunks"], 3)
            self.assertEqual(sequence, [
                item for ident in ids for item in (("put", ident), ("get", ident))]
                + [("put", parent_id)])
            _, final_parent = call(parent_id)
            final_leaves = {ident: call(ident)[1] for ident in ids}
            restored = assemble_encrypted_chunks(
                final_parent, final_leaves, note_path,
                final_parent["_rev"], phrase, salt)
            self.assertEqual(restored["content"], "".join(parts))
            self.assertEqual(restored["chunks"], 3)
            self.assertNotEqual(final_parent["_rev"], stored["_rev"])
        finally:
            if created:
                self.assertEqual(call(method="DELETE")[0], 200)


if __name__ == "__main__":
    unittest.main()
