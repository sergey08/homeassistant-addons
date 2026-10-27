"""Unit tests for isolated LiveSync CLI bridge."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from livesync_cli_bridge import prepare_put_command, put_local_only, read_local_note, verify_local_roundtrip, verify_local_cli_runtime, safe_update_local_note, list_local_note_paths, safe_create_local_note, validate_remote_configuration, prepare_official_cli_settings, install_official_cli_settings, CLIUnavailable

class TestCLIBridge(unittest.TestCase):
    def test_encrypted_remote_configuration_readiness_is_secret_free(self):
        config = {
            "couchdb_url": "http://db21ed7f-obsidian-syncserver-ssl:5984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "do-not-expose-password",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "do-not-expose-passphrase",
        }
        result = validate_remote_configuration(config)
        self.assertTrue(result["configuration_complete"])
        self.assertFalse(result["remote_writes_enabled"])
        self.assertNotIn("do-not-expose", str(result))
        config["couchdb_url"] = "http://user:password@localhost:5984"
        self.assertFalse(validate_remote_configuration(config)["configuration_complete"])
        config["couchdb_url"] = "http://localhost:5984"
        config["livesync_e2ee_passphrase"] = ""
        self.assertFalse(validate_remote_configuration(config)["configuration_complete"])

    def test_official_cli_settings_are_encrypted_and_never_auto_sync(self):
        config = {
            "couchdb_url": "http://db21ed7f-obsidian-syncserver-ssl:5984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "secret",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "phrase",
        }
        settings = prepare_official_cli_settings(config)
        self.assertTrue(settings["encrypt"])
        self.assertEqual(settings["passphrase"], "phrase")
        self.assertFalse(settings["liveSync"])
        self.assertFalse(settings["syncOnSave"])
        self.assertFalse(settings["syncOnStart"])
        config["couchdb_url"] = "http://public.example:5984"
        with self.assertRaisesRegex(CLIUnavailable, "plain_http_untrusted"):
            prepare_official_cli_settings(config)

    def test_settings_install_is_private_and_does_not_overwrite(self):
        import json
        config = {
            "couchdb_url": "https://localhost:6984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "secret",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "phrase",
        }
        with tempfile.TemporaryDirectory() as temp:
            result = install_official_cli_settings(config, temp)
            target = Path(temp) / ".livesync" / "settings.json"
            self.assertTrue(result["installed"])
            self.assertFalse(result["remote_synced"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
            self.assertTrue(json.loads(target.read_text())["encrypt"])
            with self.assertRaisesRegex(CLIUnavailable, "already_exist"):
                install_official_cli_settings(config, temp)

    def test_disposable_remote_preview_never_uses_persistent_database(self):
        from livesync_cli_bridge import fetch_remote_to_disposable_database
        config = {
            "couchdb_url": "https://localhost:6984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "secret",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "phrase",
        }
        with patch("livesync_cli_bridge.validate_cli_installation",
                   side_effect=lambda binary, database: (binary, database)):
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                with patch("livesync_cli_bridge.configure_disposable_remote_with_cli") as configure:
                    with patch("livesync_cli_bridge.list_local_note_paths",
                               return_value={"Tests/one.md": {}}):
                        result = fetch_remote_to_disposable_database(config)
                    configure.assert_called_once()
        self.assertEqual(result["paths"], ["Tests/one.md"])
        self.assertFalse(result["persistent_local_modified"])
        command = run.call_args.args[0]
        self.assertIn("fetch", command)
        self.assertIn("--force", command)
        self.assertNotIn("/data/livesync-client", command)
        self.assertFalse(Path(command[2]).exists())

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
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={"Notes/Test.md": {"conflict": False}}), patch("livesync_cli_bridge.read_local_note", return_value="remote changed"):
            with patch("livesync_cli_bridge.verify_local_roundtrip") as write:
                with self.assertRaisesRegex(CLIUnavailable, "cli_local_conflict"):
                    safe_update_local_note("/unused/index.cjs", "/unused/db",
                                           "Notes/Test.md", "old", "new")
                write.assert_not_called()

    def test_update_accepts_matching_content(self):
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={"Notes/Test.md": {"conflict": False}}), patch("livesync_cli_bridge.read_local_note", return_value="old"):
            with patch("livesync_cli_bridge.verify_local_roundtrip", return_value=True) as write:
                self.assertTrue(safe_update_local_note("/unused/index.cjs", "/unused/db",
                                                       "Notes/Test.md", "old", "new"))
                write.assert_called_once()

    def test_ls_rejects_case_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = (
                    b"Notes/Test.md\\t1\\t100\\t1-7f40ba04869446686d6874804c161a6a\\n"
                    b"notes/test.md\\t1\\t101\\t1-7f40ba04869446686d6874804c161a6b\\n"
                )
                with self.assertRaisesRegex(CLIUnavailable, "cli_list_invalid_format"):
                    list_local_note_paths(str(binary), temp)

    def test_ls_parses_documented_tabular_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"Notes/Test.md\t4\t1720000000000\t2-" + b"a" * 32 + b"\n"
                result = list_local_note_paths(str(binary), temp)
                self.assertEqual(result["Notes/Test.md"]["size"], 4)
                self.assertEqual(result["Notes/Test.md"]["revision"], "2-" + "a" * 32)

    def test_ls_accepts_literal_escaped_tabs_from_official_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"Notes/Test.md\\t4\\t1720000000000\\t2-" + b"a" * 32 + b"\n"
                result = list_local_note_paths(str(binary), temp)
                self.assertEqual(result["Notes/Test.md"]["size"], 4)

    def test_ls_rejects_non_tabular_output(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"error: database not initialized\n"
                with self.assertRaises(CLIUnavailable):
                    list_local_note_paths(str(binary), temp)

    def test_ls_conflict_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"Notes/Test.md\t4\t1720000000000\t2-" + b"a" * 32 + b"*\n"
                result = list_local_note_paths(str(binary), temp)
                self.assertTrue(result["Notes/Test.md"]["conflict"])

    def test_ls_rejects_duplicate_note_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "index.cjs"
            binary.write_text("test")
            row = b"Notes/Test.md\t4\t1720000000000\t2-" + b"a" * 32 + b"\n"
            with patch("livesync_cli_bridge.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = row + row
                with self.assertRaisesRegex(CLIUnavailable, "cli_list_invalid_format"):
                    list_local_note_paths(str(binary), temp)

    def test_create_rejects_existing_note(self):
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={"Notes/Test.md": {}}):
            with patch("livesync_cli_bridge.verify_local_roundtrip") as write:
                with self.assertRaisesRegex(CLIUnavailable, "cli_note_already_exists"):
                    safe_create_local_note("/unused/index.cjs", "/unused/db", "Notes/Test.md", "text")
                write.assert_not_called()

    def test_create_rejects_case_only_collision(self):
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={"notes/test.md": {}}):
            with patch("livesync_cli_bridge.verify_local_roundtrip") as write:
                with self.assertRaisesRegex(CLIUnavailable, "cli_note_already_exists"):
                    safe_create_local_note("/unused/index.cjs", "/unused/db", "Notes/Test.md", "text")
                write.assert_not_called()

    def test_update_rejects_conflicted_note(self):
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={"Notes/Test.md": {"conflict": True}}):
            with patch("livesync_cli_bridge.verify_local_roundtrip") as write:
                with self.assertRaisesRegex(CLIUnavailable, "cli_local_conflict"):
                    safe_update_local_note("/unused/index.cjs", "/unused/db", "Notes/Test.md", "old", "new")
                write.assert_not_called()

    def test_create_accepts_verified_absence(self):
        with patch("livesync_cli_bridge.list_local_note_paths", return_value={}):
            with patch("livesync_cli_bridge.verify_local_roundtrip", return_value=True) as write:
                self.assertTrue(safe_create_local_note("/unused/index.cjs", "/unused/db", "Notes/New.md", "text"))
                write.assert_called_once()

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
