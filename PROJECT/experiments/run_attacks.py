"""Measure attacks against the intentionally vulnerable executor."""

from .common import arguments, load_json, run_cases


def main() -> None:
    args = arguments("Run ToolGuard vulnerable attack cases", include_payloads=True)
    cases = load_json("data/attack_cases.json")
    if args.payload:
        selected = {item.upper() for item in args.payload}
        cases = [case for case in cases if case["payload"].upper() in selected]
    run_cases(
        cases,
        backend_name=args.backend,
        model=args.model,
        mode=args.mode or "vulnerable",
        repetitions=args.repetitions,
        attack=True,
    )


if __name__ == "__main__":
    main()
