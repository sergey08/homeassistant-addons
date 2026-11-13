"""Offline regression: a production ingress route cannot publish remote notes."""
import unittest
from unittest.mock import patch

from server import app


class RemotePublishDisabledTests(unittest.TestCase):
    def test_publish_is_denied_even_with_old_action_header(self):
        with app.test_client() as client:
            for headers in ({}, {"X-Obsidian-Client-Action": "publish-test-note",
                                  "Sec-Fetch-Site": "same-origin"}):
                with self.subTest(headers=headers), patch(
                    "livesync_cli_bridge.publish_isolated_test_note"
                ) as remote_publish:
                    response = client.post(
                        "/api/livesync-cli/publish-test-note", headers=headers
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.get_json()["error"], "remote_writes_disabled")
                    self.assertIs(response.get_json()["remote_writes_enabled"], False)
                    remote_publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
