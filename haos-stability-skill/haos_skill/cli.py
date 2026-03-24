from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .skill import evaluate_structure, load_schema, scan_structure
from .safety import SkillError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone HAOS structural stability skill."
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a single state specification.")
    evaluate_parser.add_argument("state_file", type=Path, help="Path to a state JSON file.")
    evaluate_parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Hard timeout budget in seconds.",
    )

    scan_parser = subparsers.add_parser("scan", help="Evaluate a batch of state specifications.")
    scan_parser.add_argument("grid_file", type=Path, help="Path to a grid JSON file.")
    scan_parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Per-case timeout budget in seconds.",
    )

    schema_parser = subparsers.add_parser("schema", help="Print the bundled tool schema.")
    schema_parser.add_argument("--pretty", action="store_true", help="Pretty-print the schema JSON.")

    return parser


def main(argv: Sequence[str] = ()) -> None:
    parser = build_parser()
    args = parser.parse_args(argv if argv else None)

    try:
        if args.command == "evaluate":
            payload = _load_json_file(args.state_file)
            _emit_json(evaluate_structure(payload, timeout=args.timeout))
            return

        if args.command == "scan":
            payload = _load_json_file(args.grid_file)
            _emit_json(scan_structure(payload, timeout=args.timeout))
            return

        if args.command == "schema":
            _emit_json(load_schema(), pretty=args.pretty)
            return
    except (FileNotFoundError, json.JSONDecodeError, SkillError) as exc:
        raise SystemExit(str(exc)) from exc

    raise SystemExit("unsupported command")


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit("%s must contain a top-level JSON object" % path)
    return payload


def _emit_json(payload: Any, pretty: bool = False) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, sort_keys=False))
        return
    print(json.dumps(payload, separators=(",", ":"), sort_keys=False))


if __name__ == "__main__":
    main()
