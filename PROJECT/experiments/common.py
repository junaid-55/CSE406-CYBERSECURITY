"""Shared experiment runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.agent import run_agent
from src.attacker import plant_attack
from src.config import ROOT, load_config
from src.evaluator import aggregate
from src.llm_client import make_client
from src.workspace import Workspace


def arguments(description: str, include_payloads: bool = False) -> argparse.Namespace:
    config = load_config()
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--backend", choices=("ollama", "deterministic"), default=config["model"]["provider"])
    parser.add_argument("--model", help="Override configured Ollama model")
    parser.add_argument("--repetitions", type=int, default=int(config["experiment"]["repetitions"]))
    parser.add_argument("--mode", choices=("vulnerable", "delimited", "defended"))
    if include_payloads:
        parser.add_argument("--payload", action="append", help="Run only this payload ID (repeatable)")
    return parser.parse_args()


def load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def run_cases(
    cases: list[dict[str, Any]],
    *,
    backend_name: str,
    model: str | None,
    mode: str,
    repetitions: int,
    attack: bool,
) -> list[dict[str, Any]]:
    if repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    config = load_config()
    if model:
        config["model"]["name"] = model
    records: list[dict[str, Any]] = []
    workspace = Workspace()
    for case in cases:
        for repetition in range(1, repetitions + 1):
            workspace.reset()
            payload = case.get("payload")
            if attack:
                plant_attack(workspace, str(payload))
            case_id = f"{case['id']}-{mode}-r{repetition}"
            print(f"\n=== {case_id} ===")
            result = run_agent(
                str(case.get("task", case.get("prompt"))),
                mode=mode,
                backend=make_client(config, backend_name),
                workspace=workspace,
                max_steps=int(config["experiment"]["max_steps"]),
                case_id=case_id,
                expected_tools=list(case.get("expected_tools", [])),
                attack_enabled=attack,
                payload_id=str(payload) if payload else None,
                trace=True,
            )
            records.append(
                {
                    "case_id": case_id,
                    "attack_enabled": attack,
                    "expected_tools": case.get("expected_tools", []),
                    "metrics": result.metrics,
                    "log_path": result.log_path,
                }
            )
            print(f"FINAL: {result.final_response}")
            print(f"LOG: {result.log_path}")
    print("\n=== SUITE METRICS ===")
    print(json.dumps(aggregate(records), indent=2))
    return records
