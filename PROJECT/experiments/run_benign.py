"""Run the benign utility task suite."""

from .common import arguments, load_json, run_cases


def main() -> None:
    args = arguments("Run ToolGuard benign tasks")
    run_cases(
        load_json("data/tasks.json"),
        backend_name=args.backend,
        model=args.model,
        mode=args.mode or "defended",
        repetitions=args.repetitions,
        attack=False,
    )


if __name__ == "__main__":
    main()
