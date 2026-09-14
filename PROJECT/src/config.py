"""Small dependency-free loader for ToolGuard's intentionally simple YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return {}
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else ROOT / "config.yaml"
    result: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, value = line.split(":", 1)
            parsed = _scalar(value)
            result[key.strip()] = parsed
            current = parsed if isinstance(parsed, dict) else None
        else:
            if current is None:
                raise ValueError(f"Invalid nested config line: {raw}")
            key, value = line.strip().split(":", 1)
            current[key.strip()] = _scalar(value)
    return result
