"""Measure prompt delimiting or firewall defense on identical attack cases."""

from .common import arguments, load_json, run_cases, select_cases


def main() -> None:
    args = arguments("Run ToolGuard defended attack cases", include_payloads=True)
    cases = select_cases(load_json("data/attack_cases.json"), args)
    run_cases(
        cases,
        backend_name=args.backend,
        model=args.model,
        mode=args.mode or "defended",
        repetitions=args.repetitions,
        attack=True,
    )


if __name__ == "__main__":
    main()
