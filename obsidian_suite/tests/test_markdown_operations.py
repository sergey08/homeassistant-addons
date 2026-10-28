"""Exercise the actual MCP note operations without requiring a running MCP server."""
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

server_path = Path(__file__).resolve().parents[1] / "server.py"
fake_mcp = types.ModuleType("mcp")
fake_server = types.ModuleType("mcp.server")
fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

class FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass
    def tool(self):
        return lambda func: func

fake_fastmcp.FastMCP = FakeFastMCP
fake_server.fastmcp = fake_fastmcp
fake_mcp.server = fake_server
with patch.dict(sys.modules, {"mcp": fake_mcp, "mcp.server": fake_server, "mcp.server.fastmcp": fake_fastmcp}):
    spec = importlib.util.spec_from_file_location("notes_under_test", server_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class MarkdownOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.vault = root / "vault"
        self.vault.mkdir()
        self.trash = root / "trash"
        self.trash.mkdir()
        module.ROOT = self.vault.resolve()
        module.TRASH = self.trash.resolve()

    def test_create_read_search_append_rename_delete_and_recovery(self):
        module.write_note("Projects/first.md", "# Test note\nimportant")
        self.assertEqual(module.list_notes(), ["Projects/first.md"])
        self.assertIn("important", module.read_note("Projects/first.md"))
        self.assertEqual(module.search_notes("important")[0]["note"], "Projects/first.md")
        module.append_note("Projects/first.md", "\nsecond line")
        self.assertIn("second line", module.read_note("Projects/first.md"))
        module.write_note("Projects/first.md", "new version", overwrite=True)
        self.assertEqual(module.read_note("Projects/first.md"), "new version")
        self.assertEqual(len(list(self.trash.rglob("first.md"))), 1)
        module.rename_note("Projects/first.md", "Knowledge/renamed.md")
        module.delete_note("Knowledge/renamed.md")
        self.assertEqual(module.list_notes(), [])
        self.assertEqual(len(list(self.trash.rglob("renamed.md"))), 1)

    def test_reject_path_escape_and_symlinks(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.vault / "alias").symlink_to(outside, target_is_directory=True)
        inside = self.vault / "inside"
        inside.mkdir()
        (self.vault / "inside-link").symlink_to(inside, target_is_directory=True)
        for path in ("../outside/x.md", "alias/x.md", "inside-link/x.md", "/tmp/x.md", ".hidden.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.write_note(path, "should not be written")
        self.assertEqual(module.list_notes(), [])

    def test_guard_detects_external_changes(self):
        module.write_note("shared.md", "first")
        old_revision = module.note_revision("shared.md")
        (self.vault / "shared.md").write_text("edited externally", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "changed since it was read"):
            module.write_note("shared.md", "agent change", overwrite=True, expected_sha256=old_revision)
        self.assertEqual(module.read_note("shared.md"), "edited externally")
        current_revision = module.note_revision("shared.md")
        module.write_note("shared.md", "agent change", overwrite=True, expected_sha256=current_revision)
        self.assertEqual(module.read_note("shared.md"), "agent change")

    def test_guard_applies_to_append_rename_delete(self):
        module.write_note("guarded.md", "initial")
        revision = module.note_revision("guarded.md")
        (self.vault / "guarded.md").write_text("external edit", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            module.append_note("guarded.md", "should not append", expected_sha256=revision)
        with self.assertRaises(RuntimeError):
            module.rename_note("guarded.md", "renamed.md", expected_sha256=revision)
        with self.assertRaises(RuntimeError):
            module.delete_note("guarded.md", expected_sha256=revision)
        self.assertEqual(module.read_note("guarded.md"), "external edit")
        fresh = module.note_revision("guarded.md")
        module.append_note("guarded.md", "\\nnew line", expected_sha256=fresh)
        self.assertIn("new line", module.read_note("guarded.md"))

    def test_reject_overwrite_without_permission(self):
        module.write_note("existing.md", "original")
        with self.assertRaises(FileExistsError):
            module.write_note("existing.md", "changed")
        self.assertEqual(module.read_note("existing.md"), "original")


if __name__ == "__main__":
    unittest.main()
