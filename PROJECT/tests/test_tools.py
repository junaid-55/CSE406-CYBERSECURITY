from __future__ import annotations

import unittest

from src.tools import ToolError, ToolExecutor
from tests.helpers import TemporaryWorkspace


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TemporaryWorkspace()
        self.tools = ToolExecutor(self.fixture.workspace)

    def tearDown(self) -> None:
        self.fixture.close()

    def test_list_and_read_are_deterministic(self) -> None:
        messages = self.tools.list_emails()
        self.assertEqual([1, 2], [item["id"] for item in messages])
        self.assertNotIn("body", messages[0])
        self.assertEqual("Submission reminder", self.tools.read_email(2)["subject"])

    def test_send_changes_only_mock_outbox(self) -> None:
        result = self.tools.send_email("bob@demo.local", "Test", "Hello")
        self.assertEqual("sent_in_mock_workspace", result["status"])
        self.assertEqual(1, len(self.fixture.state()["sent_emails"]))

    def test_invalid_tool_arguments_are_rejected(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.read_email(True)
        with self.assertRaises(ToolError):
            self.tools.send_email("invalid", "Subject", "Body")
        with self.assertRaises(ToolError):
            self.tools.execute("shell", {})


if __name__ == "__main__":
    unittest.main()
