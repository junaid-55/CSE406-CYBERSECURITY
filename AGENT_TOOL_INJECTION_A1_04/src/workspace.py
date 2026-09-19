"""Persistent, deterministic mock email workspace."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import ROOT, load_config


class Workspace:
    def __init__(self, path: str | Path | None = None, baseline: str | Path | None = None):
        config = load_config()["environment"]
        self.path = Path(path or ROOT / config["workspace_file"])
        self.baseline = Path(baseline or ROOT / config["baseline_file"])
        if not self.path.exists():
            self.reset()

    def load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

    def reset(self) -> dict[str, Any]:
        state = json.loads(self.baseline.read_text(encoding="utf-8"))
        self.save(state)
        return copy.deepcopy(state)

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.load())

    def insert_email(self, sender: str, subject: str, body: str) -> dict[str, Any]:
        state = self.load()
        email = {
            "id": int(state["next_email_id"]),
            "from": sender,
            "to": state["profile"]["email"],
            "subject": subject,
            "body": body,
            "timestamp": "2026-09-09T09:00:00+06:00",
        }
        state["next_email_id"] = email["id"] + 1
        state["emails"].append(email)
        self.save(state)
        return copy.deepcopy(email)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or reset the mock workspace")
    parser.add_argument("action", choices=("show", "reset"))
    parser.add_argument("--workspace")
    args = parser.parse_args()
    workspace = Workspace(args.workspace)
    state = workspace.reset() if args.action == "reset" else workspace.load()
    print(json.dumps(state, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
