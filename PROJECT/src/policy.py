"""Deterministic capability policy enforced outside the language model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .tools import TOOL_POLICY


@dataclass(frozen=True)
class PolicyDecision:
    tool: str
    action: str
    reason: str
    allowed_tools: tuple[str, ...]
    sensitive: bool

    @property
    def allowed(self) -> bool:
        return self.action in {"allow", "confirm"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "action": self.action,
            "reason": self.reason,
            "allowed_tools": list(self.allowed_tools),
            "sensitive": self.sensitive,
        }


def capabilities_for_task(user_prompt: str) -> set[str]:
    """Map the original user request to the minimum required capabilities.

    This deliberately small, auditable parser is the trusted baseline for the
    fixed experiment task set. Unknown requests receive no capability.
    """

    text = " ".join(user_prompt.lower().split())
    allowed: set[str] = set()

    wants_send = bool(re.search(r"\b(send|email|mail|forward|reply)\b", text)) and bool(
        re.search(r"\b(send|forward|reply)\b", text)
    )
    wants_profile = bool(re.search(r"\b(profile|demo profile|my details)\b", text))
    wants_email_read = bool(
        re.search(r"\b(summar(?:y|ize)|read|newest|latest|who sent|sender)\b", text)
        and re.search(r"\b(email|inbox|message)\b", text)
    )
    wants_list = bool(
        re.search(r"\b(list|subjects?|all emails|inbox|newest|latest)\b", text)
        and re.search(r"\b(email|emails|inbox|subjects?|message)\b", text)
    )

    if wants_list:
        allowed.add("list_emails")
    if wants_email_read:
        allowed.add("read_email")
        if re.search(r"\b(newest|latest)\b", text):
            allowed.add("list_emails")
    if wants_profile:
        allowed.add("get_demo_profile")
    if wants_send:
        allowed.add("send_email")

    # Sending a summary or content from an email legitimately needs reads too.
    if wants_send and re.search(r"\b(summary|summarize|content|email id|latest|newest)\b", text):
        allowed.add("read_email")
        if re.search(r"\b(latest|newest)\b", text):
            allowed.add("list_emails")
    return allowed


class ToolFirewall:
    def __init__(
        self,
        user_prompt: str,
        mode: str = "defended",
        require_confirmation: bool = False,
        confirmer: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        if mode not in {"vulnerable", "delimited", "defended"}:
            raise ValueError(f"Unknown security mode: {mode}")
        self.mode = mode
        self.allowed_tools = capabilities_for_task(user_prompt)
        self.require_confirmation = require_confirmation
        self.confirmer = confirmer

    def decide(self, tool: str, arguments: dict[str, Any]) -> PolicyDecision:
        metadata = TOOL_POLICY.get(tool)
        if metadata is None:
            return PolicyDecision(
                tool, "block", "Unknown tools are never executable", tuple(sorted(self.allowed_tools)), True
            )
        sensitive = bool(metadata["sensitive"] or metadata["type"] == "write")
        if self.mode in {"vulnerable", "delimited"}:
            return PolicyDecision(
                tool,
                "allow",
                f"{self.mode} mode exposes all registered tools",
                tuple(sorted(TOOL_POLICY)),
                sensitive,
            )
        if tool not in self.allowed_tools:
            return PolicyDecision(
                tool,
                "block",
                "Tool is not required by the original user request",
                tuple(sorted(self.allowed_tools)),
                sensitive,
            )
        if sensitive and self.require_confirmation:
            approved = bool(self.confirmer and self.confirmer(tool, arguments))
            return PolicyDecision(
                tool,
                "allow" if approved else "block",
                "User approved sensitive action" if approved else "Sensitive action was not confirmed",
                tuple(sorted(self.allowed_tools)),
                sensitive,
            )
        return PolicyDecision(
            tool,
            "allow",
            "Tool is required by the original user request",
            tuple(sorted(self.allowed_tools)),
            sensitive,
        )
