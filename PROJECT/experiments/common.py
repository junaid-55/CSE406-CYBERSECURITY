"""Shared experiment runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.agent import run_agent
from src.attacker import plant_attack
from src.config import ROOT, load_config
from src.payloads import PAYLOADS, payload_target
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
        parser.add_argument(
            "--task",
            help=(
                "Override the user prompt for every selected case. Required when a "
                "--payload has no entry in data/attack_cases.json."
            ),
        )
        parser.add_argument(
            "--expect",
            action="append",
            help="Expected tool for --task, repeatable; defaults to list_emails and read_email",
        )
    return parser.parse_args()


def select_cases(cases: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """Filter cases by --payload, synthesizing one for any payload with no case.

    This is what makes ad-hoc T-series runs possible: a payload only needs an
    entry in src/payloads.py, and the prompt comes from --task on the command
    line rather than from data/attack_cases.json.
    """

    task = getattr(args, "task", None)
    expected = list(getattr(args, "expect", None) or []) or ["list_emails", "read_email"]
    if not args.payload:
        selected = cases
    else:
        wanted = [item.upper() for item in args.payload]
        unknown = [pid for pid in wanted if pid not in PAYLOADS]
        if unknown:
            raise SystemExit(
                f"Unknown payload(s): {', '.join(unknown)}. Defined payloads: {', '.join(PAYLOADS)}"
            )
        by_payload = {case["payload"].upper(): case for case in cases}
        selected = []
        for payload_id in wanted:
            case = by_payload.get(payload_id)
            if case is None:
                if not task:
                    raise SystemExit(
                        f"Payload {payload_id} has no case in data/attack_cases.json; "
                        f"pass --task \"...\" to supply the user prompt."
                    )
                case = {
                    "id": f"AT-{payload_id}",
                    "payload": payload_id,
                    "task": task,
                    "expected_tools": expected,
                    "goal": "ad_hoc",
                }
            selected.append(case)
    if task:
        selected = [dict(case, task=task, expected_tools=expected) for case in selected]
    return selected


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
            channel, recipient, marker, absent = (
                payload_target(str(payload)) if payload else ("email", None, None, [])
            )
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
                attack_recipient=recipient,
                attack_marker=marker,
                attack_channel=channel,
                attack_absent=absent,
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
