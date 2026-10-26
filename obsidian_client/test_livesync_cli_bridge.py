"""Unit tests for isolated LiveSync CLI bridge."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from livesync_cli_bridge import prepare_put_command, put_local_only, read_local_note, verify_local_roundtrip, verify_local_cli_runtime, safe_update_local_note, list_local_note_paths, CLIUnavailable

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
                self.assertEqual(args[0], ["/usr/local/bin/node", str(binary), str(database),
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

    def test_cli_runtime_help_never_syncs(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                self.assertTrue(verify_local_cli_runtime(str(binary), temp))
                self.assertEqual(run.call_args.args[0], ["/usr/local/bin/node", str(binary), "--help"])

    def test_update_rejects_stale_content_without_writing(self):
        with patch("livesync_cli_bridge.read_local_note", return_value="remote changed"):
            with patch("livesync_cli_bridge.verify_local_roundtrip") as write:
                with self.assertRaisesRegex(CLIUnavailable, "cli_local_conflict"):
                    safe_update_local_note("/unused/index.cjs", "/unused/db",
                                           "Notes/Test.md", "old", "new")
                write.assert_not_called()

    def test_update_accepts_matching_content(self):
        with patch("livesync_cli_bridge.read_local_note", return_value="old"):
            with patch("livesync_cli_bridge.verify_local_roundtrip", return_value=True) as write:
                self.assertTrue(safe_update_local_note("/unused/index.cjs", "/unused/db",
                                                       "Notes/Test.md", "old", "new"))
                write.assert_called_once()

    def test_ls_parses_documented_tabular_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"Notes/Test.md\\t4\\t1720000000000\\t2-" + b"a" * 32 + b"\\n"
                result = list_local_note_paths(str(binary), temp)
                self.assertEqual(result["Notes/Test.md"]["size"], 4)
                self.assertEqual(result["Notes/Test.md"]["revision"], "2-" + "a" * 32)

    def test_ls_rejects_non_tabular_output(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"error: database not initialized\\n"
                with self.assertRaises(CLIUnavailable):
                    list_local_note_paths(str(binary), temp)

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
