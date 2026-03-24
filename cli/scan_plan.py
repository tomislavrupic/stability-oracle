from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oracle.report import scan_trajectory
from oracle.trajectory import TrajectoryValidationError, load_trajectory_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan a trajectory plan for stability signals.")
    parser.add_argument("plan", type=Path, help="Path to a trajectory JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit the scan report as JSON.")
    parser.add_argument(
        "--with-recovery",
        action="store_true",
        help="Include recovery simulation in the report.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        spec = load_trajectory_file(args.plan)
        report = scan_trajectory(spec, include_recovery=args.with_recovery)
    except (TrajectoryValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=False))
    else:
        print(report.render_text())


if __name__ == "__main__":
    main()
