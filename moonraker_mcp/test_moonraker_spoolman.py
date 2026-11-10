"""Unit tests for narrowly scoped, read-only Spoolman inventory access."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from moonraker_spoolman import SpoolmanReadError, list_spoolman_inventory, MAX_RESPONSE_BYTES


class Response:
    def __init__(self, data):
        self.stream = io.BytesIO(data)
    def __enter__(self):
        return self.stream
    def __exit__(self, *args):
        self.stream.close()


class SpoolmanInventoryTests(unittest.TestCase):
    def sample(self):
        return [{"id": 17, "archived": False, "remaining_weight": 320.563,
                 "used_weight": 679.437,
                 "filament": {"name": "PLA+", "material": "PLA", "color_hex": "00AAFF",
                              "vendor": {"name": "Example",
                                         "website": "https://private.example"}} ,
                 "extra": {"private": "should not escape"}}]

    def call(self, payload, captures=None):
        def opener(req, timeout):
            self.assertEqual(timeout, 10)
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.full_url, "http://printer.local:7125/server/spoolman/proxy")
            request_body = json.loads(req.data)
            self.assertEqual(request_body["request_method"], "GET")
            self.assertEqual(request_body["path"], "/v1/spool")
            self.assertEqual(request_body["use_v2_response"], True)
            self.assertNotIn("query", request_body)
            self.assertNotIn("body", request_body)
            if captures is not None:
                captures.append(req)
            return Response(json.dumps(payload).encode("utf-8"))
        return list_spoolman_inventory("http://printer.local:7125", "test-api-key", opener)

    def test_whitelisted_spool_fields_only(self):
        captured = []
        result = self.call({"result": {"response": self.sample(), "error": None}}, captured)
        self.assertEqual(result["count"], 1)
        spool = result["spools"][0]
        self.assertEqual(spool["remaining_weight_g"], 320.56)
        self.assertEqual(spool["filament"]["material"], "PLA")
        self.assertEqual(spool["filament"]["vendor"], "Example")
        self.assertNotIn("extra", spool)
        self.assertNotIn("website", str(result))
        self.assertEqual(captured[0].get_header("X-api-key"), "test-api-key")

    def test_empty_spools(self):
        result = self.call({"result": {"response": [], "error": None}})
        self.assertEqual(result, {"count": 0, "spools": []})

    def test_fail_closed_on_spoolman_error(self):
        with self.assertRaises(SpoolmanReadError):
            self.call({"result": {"response": None, "error": {"status_code": 503}}})

    def test_fail_closed_on_malformed_records(self):
        with self.assertRaises(SpoolmanReadError):
            self.call({"result": {"response": [{"id": True}], "error": None}})

    def test_fail_closed_on_more_than_100(self):
        with self.assertRaises(SpoolmanReadError):
            self.call({"result": {"response": [{"id": n} for n in range(101)], "error": None}})

    def test_rejects_unexpected_response(self):
        with self.assertRaises(SpoolmanReadError):
            self.call({"result": {"response": {"id": 1}, "error": None}})

    def test_rejects_response_too_large(self):
        def oversized(req, timeout):
            return Response(b" " * (MAX_RESPONSE_BYTES + 1))
        with self.assertRaises(SpoolmanReadError):
            list_spoolman_inventory("http://printer.local:7125", opener=oversized)

    def test_rejects_url_with_credentials_and_path(self):
        for address in ("http://user:pass@printer.local:7125",
                        "http://printer.local:7125/some/endpoint",
                        "file:///etc/passwd"):
            with self.subTest(address=address):
                with self.assertRaises(SpoolmanReadError):
                    list_spoolman_inventory(address)

    def test_no_redirects(self):
        from moonraker_files import _NoRedirect
        request = __import__("urllib.request", fromlist=["Request"]).Request("http://printer.local")
        self.assertRaises(Exception, _NoRedirect().redirect_request,
                          request, None, 302, "Found", {}, "http://elsewhere/")


if __name__ == "__main__":
    unittest.main()
