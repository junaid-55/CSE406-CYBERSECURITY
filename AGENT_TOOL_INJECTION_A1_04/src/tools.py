"""Student-implemented tools and their security metadata."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from .workspace import Workspace


class ToolError(ValueError):
    pass


TOOL_POLICY: dict[str, dict[str, Any]] = {
    "list_emails": {"type": "read", "sensitive": False},
    "read_email": {"type": "read", "sensitive": False},
    "get_demo_profile": {"type": "read", "sensitive": True},
    "send_email": {"type": "write", "sensitive": True},
}


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_emails",
            "description": "List inbox email metadata, newest last. Does not return bodies.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read one mock inbox email by integer ID.",
            "parameters": {
                "type": "object",
                "properties": {"email_id": {"type": "integer"}},
                "required": ["email_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_demo_profile",
            "description": "Read the local fictional user's sensitive demo profile.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email only inside the local mock workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]


@dataclass
class ToolExecutor:
    workspace: Workspace

    def list_emails(self) -> list[dict[str, Any]]:
        state = self.workspace.load()
        return [
            {key: email[key] for key in ("id", "from", "subject", "timestamp")}
            for email in state["emails"]
        ]

    def read_email(self, email_id: int) -> dict[str, Any]:
        if isinstance(email_id, bool) or not isinstance(email_id, int):
            raise ToolError("email_id must be an integer")
        for email in self.workspace.load()["emails"]:
            if email["id"] == email_id:
                return copy.deepcopy(email)
        raise ToolError(f"Email ID {email_id} does not exist")

    def get_demo_profile(self) -> dict[str, Any]:
        return copy.deepcopy(self.workspace.load()["profile"])

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        for label, value in (("to", to), ("subject", subject), ("body", body)):
            if not isinstance(value, str) or not value.strip():
                raise ToolError(f"{label} must be a non-empty string")
        if "@" not in to or any(character in to for character in "\r\n"):
            raise ToolError("to must be a single valid demo address")
        state = self.workspace.load()
        sent = {
            "id": len(state["sent_emails"]) + 1,
            "from": state["profile"]["email"],
            "to": to.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
        }
        state["sent_emails"].append(sent)
        self.workspace.save(state)
        return {"status": "sent_in_mock_workspace", "message": copy.deepcopy(sent)}

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        functions: dict[str, Callable[..., Any]] = {
            "list_emails": self.list_emails,
            "read_email": self.read_email,
            "get_demo_profile": self.get_demo_profile,
            "send_email": self.send_email,
        }
        if name not in functions:
            raise ToolError(f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise ToolError("Tool arguments must be an object")
        try:
            return functions[name](**arguments)
        except TypeError as error:
            raise ToolError(f"Invalid arguments for {name}: {error}") from error
