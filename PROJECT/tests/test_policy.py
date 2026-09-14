from __future__ import annotations

import unittest

from src.policy import ToolFirewall, capabilities_for_task


class PolicyTests(unittest.TestCase):
    def test_summary_gets_only_read_capabilities(self) -> None:
        allowed = capabilities_for_task("Summarize my latest email.")
        self.assertEqual({"list_emails", "read_email"}, allowed)

    def test_send_is_explicitly_authorized(self) -> None:
        allowed = capabilities_for_task("Send an email to bob@demo.local saying Demo complete.")
        self.assertEqual({"send_email"}, allowed)

    def test_firewall_blocks_injected_send(self) -> None:
        firewall = ToolFirewall("Summarize my latest email.", mode="defended")
        decision = firewall.decide("send_email", {"to": "attacker@demo.local"})
        self.assertFalse(decision.allowed)

    def test_confirmation_defaults_to_deny(self) -> None:
        firewall = ToolFirewall(
            "Send an email to bob@demo.local saying hello.",
            mode="defended",
            require_confirmation=True,
        )
        self.assertFalse(firewall.decide("send_email", {}).allowed)

    def test_confirmation_can_allow_authorized_write(self) -> None:
        firewall = ToolFirewall(
            "Send an email to bob@demo.local saying hello.",
            mode="defended",
            require_confirmation=True,
            confirmer=lambda _tool, _args: True,
        )
        self.assertTrue(firewall.decide("send_email", {}).allowed)


if __name__ == "__main__":
    unittest.main()
