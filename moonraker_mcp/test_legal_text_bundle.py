"""Offline tests for third-party legal text archive integrity."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from legal_text_bundle import collect_texts


class LegalBundleTests(unittest.TestCase):
    def test_verified_legal_text_only_in_zip(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            module=base/"module"
            module.mkdir()
            raw=b"Copyright and sample license text"
            (module/"LICENSE").write_bytes(raw)
            digest=hashlib.sha256(raw).hexdigest()
            class Result:
                returncode=0
                stdout=json.dumps({"Path":"example.com/repo","Version":"v1.0.0",
                                   "Sum":"h1:testsum","Dir":str(module)})
            def runner(*args,**kwargs):
                return Result()
            row={"source_status":"SOURCE_LICENSE_FILES_FOUND","bom_ref":"component-1",
                 "name":"example.com/repo","purl":"pkg:golang/example.com/repo@v1.0.0",
                 "version":"v1.0.0","module_sum":"h1:testsum","license_file":"LICENSE",
                 "license_sha256":digest,"license_bytes":str(len(raw))}
            path=base/"legal.zip"
            summary=collect_texts([row],path,runner=runner)
            self.assertEqual(summary["modules_with_files"],1)
            self.assertFalse(summary["release_approved"])
            with ZipFile(path) as archive:
                self.assertEqual(archive.read("legal/0000/LICENSE"),raw)
                self.assertFalse(json.loads(archive.read("MANIFEST.json"))["release_approved"])

    def test_file_modified_since_hash_causes_failure(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            module=base/"module"
            module.mkdir()
            (module/"NOTICE").write_bytes(b"different")
            class Result:
                returncode=0
                stdout=json.dumps({"Path":"example.com/repo","Version":"v1.0.0",
                                   "Sum":"h1:testsum","Dir":str(module)})
            row={"source_status":"SOURCE_LICENSE_FILES_FOUND","bom_ref":"x",
                 "purl":"pkg:golang/example.com/repo@v1.0.0","version":"v1.0.0",
                 "module_sum":"h1:testsum","license_file":"NOTICE",
                 "license_sha256":"0"*64,"license_bytes":"9"}
            with self.assertRaises(ValueError):
                collect_texts([row],base/"out.zip",runner=lambda *a,**k:Result())

    def test_reject_traversal_and_changed_identity(self):
        with tempfile.TemporaryDirectory() as d:
            row={"source_status":"SOURCE_LICENSE_FILES_FOUND","bom_ref":"x",
                 "purl":"pkg:golang/example.com/repo@v1.0.0","version":"v1.0.0",
                 "module_sum":"h1:testsum","license_file":"../secret",
                 "license_sha256":"0"*64,"license_bytes":"1"}
            with self.assertRaises(ValueError):
                collect_texts([row],Path(d)/"out.zip",runner=lambda *a,**k:None)

if __name__=="__main__":
    unittest.main()
