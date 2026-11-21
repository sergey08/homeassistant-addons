"""Offline staging regression: exact bytes, base64 and SHA-256, no printer."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from moonraker_chunk_staging import stage_chunk
from moonraker_upload import UploadError


class ChunkStagingTests(unittest.TestCase):
    def test_short_dwells_end_to_end(self):
        payload = (
            b"; Safe Print diagnostic - 60 short dwells of 5 seconds\n"
            b"; No heating, movement or extrusion\n"
            + b"G4 P5000\n" * 60
            + b"; End\n"
        )
        self.assertEqual(len(payload), 637)
        digest = hashlib.sha256(payload).hexdigest()
        self.assertEqual(digest, "309b0adf7bea4707a68fcbc3fc8f6733c1eccc8e88f381da2a2b059cf84976de")
        with tempfile.TemporaryDirectory() as directory:
            Path(directory).chmod(0o700)
            result = stage_chunk(
                "safeprint_short_dwells_verified.gcode", digest, 0,
                base64.b64encode(payload).decode("ascii"), True,
                directory=directory,
            )
            self.assertTrue(result["complete"])
            self.assertEqual(result["received_bytes"], len(payload))
            self.assertEqual(
                (Path(directory) / "safeprint_short_dwells_verified.gcode").read_bytes(),
                payload,
            )

    def test_wrong_hash_is_rejected(self):
        payload = b"G4 P5000\n"
        with tempfile.TemporaryDirectory() as directory:
            Path(directory).chmod(0o700)
            with self.assertRaisesRegex(UploadError, "SHA-256 mismatch"):
                stage_chunk("bad.gcode", "0" * 64, 0,
                            base64.b64encode(payload).decode("ascii"),
                            True, directory=directory)


if __name__ == "__main__":
    unittest.main()
