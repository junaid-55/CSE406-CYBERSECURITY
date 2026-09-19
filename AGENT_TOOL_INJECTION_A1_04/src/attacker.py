"""Attacker CLI: modifies external data but never invokes victim tools."""

from __future__ import annotations

import argparse
import json

from .payloads import PAYLOADS, PAYLOAD_VERSION, get_payload
from .workspace import Workspace


def plant_attack(workspace: Workspace, payload_id: str, custom_body: str | None = None) -> dict:
    if custom_body is not None:
        payload = {"subject": "External message", "body": custom_body}
    else:
        payload = get_payload(payload_id)
    return workspace.insert_email(
        sender="external@demo.local", subject=payload["subject"], body=payload["body"]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Plant attacker-controlled mock email data")
    parser.add_argument("--payload", default="A2", choices=tuple(PAYLOADS))
    parser.add_argument("--custom", help="Use a custom body instead of the selected payload")
    parser.add_argument("--workspace")
    args = parser.parse_args()
    email = plant_attack(Workspace(args.workspace), args.payload, args.custom)
    print("[+] Malicious email inserted into the mock inbox")
    print(f"    payload_version={PAYLOAD_VERSION} email_id={email['id']}")
    print(json.dumps(email, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
