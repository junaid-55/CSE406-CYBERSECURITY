from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.config import ROOT
from src.workspace import Workspace


class TemporaryWorkspace:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        directory = Path(self.temp.name)
        baseline = directory / "baseline.json"
        baseline.write_text((ROOT / "data/benign_workspace.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.logs = directory / "logs"
        self.workspace = Workspace(directory / "workspace.json", baseline)

    def close(self) -> None:
        self.temp.cleanup()

    def state(self) -> dict:
        return json.loads(self.workspace.path.read_text(encoding="utf-8"))
