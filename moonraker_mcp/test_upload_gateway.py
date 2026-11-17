"""Offline gateway authorization tests for staged G-code upload."""
import copy
import unittest

from gateway import check_message, filter_reply, RESERVED_UPLOAD_TOOL, STAGE_CHUNK_TOOL, ABORT_STAGE_TOOL
from tool_policy import PolicyError


class GatewayUploadTests(unittest.TestCase):
    def setUp(self):
        self.args = {"filename": "sample.gcode", "sha256": "a" * 64,
                     "confirmation": "CONFIRM_UPLOAD"}
        self.msg = {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                    "params": {"name": RESERVED_UPLOAD_TOOL,
                               "arguments": self.args}}
        self.allowed = frozenset({RESERVED_UPLOAD_TOOL})

    def test_stage_chunk_requires_separate_confirmation_and_permission(self):
        args = {"filename": "sample.gcode", "sha256": "a" * 64,
                "offset": 0, "chunk_b64": "RzI4Cg==", "final": True,
                "confirmation": "CONFIRM_STAGE"}
        msg = {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
               "params": {"name": STAGE_CHUNK_TOOL, "arguments": args}}
        with self.assertRaises(PolicyError):
            check_message(msg, frozenset())
        self.assertEqual(check_message(msg, frozenset({STAGE_CHUNK_TOOL})), "tools/call")
        args["confirmation"] = "CONFIRM_UPLOAD"
        with self.assertRaises(PolicyError):
            check_message(msg, frozenset({STAGE_CHUNK_TOOL}))

    def test_abort_requires_independent_confirmation_and_permission(self):
        args = {"filename": "sample.gcode", "sha256": "a" * 64,
                "confirmation": "CONFIRM_ABORT_STAGE"}
        msg = {"jsonrpc": "2.0", "id": 12, "method": "tools/call",
               "params": {"name": ABORT_STAGE_TOOL, "arguments": args}}
        with self.assertRaises(PolicyError):
            check_message(msg, frozenset())
        self.assertEqual(check_message(msg, frozenset({ABORT_STAGE_TOOL})), "tools/call")
        args["confirmation"] = "CONFIRM_UPLOAD"
        with self.assertRaises(PolicyError):
            check_message(msg, frozenset({ABORT_STAGE_TOOL}))

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
        self.assertNotIn(STAGE_CHUNK_TOOL, hidden_names)
        self.assertNotIn(ABORT_STAGE_TOOL, hidden_names)
        self.assertEqual(shown_names.count(RESERVED_UPLOAD_TOOL), 1)
        self.assertEqual(shown_names.count(STAGE_CHUNK_TOOL), 0)
        abort = filter_reply("tools/list", copy.deepcopy(upstream), frozenset({ABORT_STAGE_TOOL}))
        self.assertEqual([x["name"] for x in abort["result"]["tools"]].count(ABORT_STAGE_TOOL), 1)
        both = filter_reply("tools/list", copy.deepcopy(upstream), self.allowed | {STAGE_CHUNK_TOOL})
        self.assertEqual([x["name"] for x in both["result"]["tools"]].count(STAGE_CHUNK_TOOL), 1)


if __name__ == "__main__":
    unittest.main()
