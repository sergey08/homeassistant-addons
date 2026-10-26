"""Unit tests for isolated LiveSync CLI bridge."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from livesync_cli_bridge import prepare_put_command, put_local_only, read_local_note, verify_local_roundtrip, CLIUnavailable

class TestCLIBridge(unittest.TestCase):
    def test_local_put_never_syncs(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            database = Path(temp) / "db"
            database.mkdir()
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                self.assertTrue(put_local_only(str(binary), str(database),
                                               "Notas/Prueba.md", "Texto"))
                args, kwargs = run.call_args
                self.assertEqual(args[0], ["node", str(binary), str(database),
                                            "put", "Notas/Prueba.md"])
                self.assertEqual(kwargs["input"], "Texto")
                self.assertFalse(kwargs["shell"])

    def test_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"Hola"
                self.assertEqual(read_local_note(str(binary), temp, "Nota.md"), "Hola")
                self.assertEqual(run.call_args.args[0][3], "cat")

    def test_roundtrip_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"incorrecto"
                with self.assertRaises(CLIUnavailable):
                    verify_local_roundtrip(str(binary), temp, "Nota.md", "correcto")

    def test_missing_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(CLIUnavailable):
                prepare_put_command("/missing/livesync-cli", temp, "Nota.md")

    def test_bad_path_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with self.assertRaises(Exception):
                prepare_put_command(str(binary), temp, "../escape.md")

if __name__ == "__main__":
    unittest.main()
