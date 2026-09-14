"""Structured, atomic JSON experiment logging."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLogger:
    def __init__(self, case_id: str, directory: str | Path | None = None) -> None:
        self.case_id = case_id
        self.directory = Path(directory or ROOT / "logs")
        self.started_at = utc_now()
        self.events: list[dict[str, Any]] = []

    def event(self, kind: str, **details: Any) -> None:
        self.events.append({"at": utc_now(), "kind": kind, **details})

    def write(self, record: dict[str, Any]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        safe_case = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.case_id)
        destination = self.directory / f"{stamp}_{safe_case}.json"
        document = {
            "schema_version": 1,
            "case_id": self.case_id,
            "started_at": self.started_at,
            "finished_at": utc_now(),
            "events": self.events,
            **record,
        }
        fd, temporary_name = tempfile.mkstemp(prefix=".toolguard-log-", dir=self.directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        return destination
