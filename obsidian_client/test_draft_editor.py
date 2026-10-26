"""Regression tests for safe Markdown draft HTML generation."""
import unittest
from unittest.mock import patch
from server import app

class TestDraftEditor(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_markdown_cannot_escape_script_or_textarea(self):
        dangerous = '</script><script>alert("x")</script>\n</textarea><h1>injected</h1>'
        with patch("server.read_encrypted_note", return_value=(dangerous, None)):
            response = self.client.get("/remote/edit?path=Demo%2FNote.md")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertNotIn('</script><script>alert', page)
        self.assertNotIn('</textarea><h1>injected', page)
        self.assertIn('u003c/script>', page)

    def test_new_draft_route_is_validated(self):
        valid = self.client.get("/remote/new?path=Viajes%2FIndonesia.md")
        self.assertEqual(valid.status_code, 200)
        self.assertIn('id="editor"', valid.get_data(as_text=True))
        for path in ("../secreto.md", "/absolute.md", "note.txt", ".hidden.md"):
            with self.subTest(path=path):
                result = self.client.get("/remote/new", query_string={"path": path})
                self.assertEqual(result.status_code, 400)

    def test_new_draft_escapes_path(self):
        response = self.client.get("/remote/new", query_string={"path": 'A/<script>alert(1)</script>.md'})
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('u003cscript>', page)

    def test_failed_read_does_not_render_editor(self):
        with patch("server.read_encrypted_note", return_value=(None, "not_found")):
            response = self.client.get("/remote/edit?path=missing.md")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('id="editor"', response.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main()
