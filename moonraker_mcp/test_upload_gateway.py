"""Offline gateway authorization tests for staged G-code upload."""
import copy
import unittest

from gateway import check_message, filter_reply, RESERVED_UPLOAD_TOOL
from tool_policy import PolicyError


class GatewayUploadTests(unittest.TestCase):
    def setUp(self):
        self.args = {"filename": "sample.gcode", "sha256": "a" * 64,
                     "confirmation": "CONFIRM_UPLOAD"}
        self.msg = {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                    "params": {"name": RESERVED_UPLOAD_TOOL,
                               "arguments": self.args}}
        self.allowed = frozenset({RESERVED_UPLOAD_TOOL})

    def test_explicit_approval_required(self):
        self.assertEqual(check_message(self.msg, self.allowed), "tools/call")
        for invalid in ("yes", "", "CONFIRM_START"):
            msg = copy.deepcopy(self.msg)
            msg["params"]["arguments"]["confirmation"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(PolicyError):
                check_message(msg, self.allowed)

    def test_tool_not_authorized_by_default(self):
        with self.assertRaises(PolicyError):
            check_message(self.msg, frozenset())

    def test_extra_missing_and_nonstring_arguments_rejected(self):
        for key in ("filename", "sha256", "confirmation"):
            msg = copy.deepcopy(self.msg)
            del msg["params"]["arguments"][key]
            with self.subTest(missing=key), self.assertRaises(PolicyError):
                check_message(msg, self.allowed)
        msg = copy.deepcopy(self.msg)
        msg["params"]["arguments"]["path"] = "/etc/passwd"
        with self.assertRaises(PolicyError):
            check_message(msg, self.allowed)
        msg = copy.deepcopy(self.msg)
        msg["params"]["arguments"]["sha256"] = 123
        with self.assertRaises(PolicyError):
            check_message(msg, self.allowed)

    def test_tools_list_exposes_upload_only_when_allowed(self):
        upstream = {"jsonrpc": "2.0", "id": 9, "result": {"tools": []}}
        hidden = filter_reply("tools/list", copy.deepcopy(upstream), frozenset())
        shown = filter_reply("tools/list", copy.deepcopy(upstream), self.allowed)
        hidden_names = [x["name"] for x in hidden["result"]["tools"]]
        shown_names = [x["name"] for x in shown["result"]["tools"]]
        self.assertNotIn(RESERVED_UPLOAD_TOOL, hidden_names)
        self.assertEqual(shown_names.count(RESERVED_UPLOAD_TOOL), 1)


if __name__ == "__main__":
    unittest.main()
