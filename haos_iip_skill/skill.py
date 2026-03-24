from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from importlib.resources import files
import json
from pathlib import Path
import signal
import sys
import threading
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oracle.report import ScanReport, scan_trajectory
from oracle.trajectory import TrajectorySpec, TrajectoryValidationError


DEFAULT_TIMEOUT_SECONDS = 2.0


class SkillInputError(ValueError):
    """Raised when skill payloads fail structural validation."""


class SkillTimeoutError(TimeoutError):
    """Raised when a bounded evaluation exceeds the configured timeout."""


@dataclass(frozen=True)
class StabilityReport:
    classification: str
    structural_retention: float
    temporal_consistency: float
    causal_deformation: float
    geometric_integrity: float
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_schema() -> dict[str, Any]:
    schema_path = files("haos_iip_skill").joinpath("schema.json")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def evaluate_structure(
    state_spec: Mapping[str, Any] | TrajectorySpec,
    timeout_seconds: float | None = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    spec = _coerce_state_spec(state_spec)
    normalized_timeout = _normalize_timeout(timeout_seconds)
    report = _run_with_timeout(lambda: _evaluate_spec(spec), normalized_timeout)
    return _translate_report(report).to_dict()


def scan_structure(
    parameter_grid: Mapping[str, Any] | Sequence[Any],
    timeout_seconds: float | None = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    cases, grid_timeout = _coerce_cases(parameter_grid, timeout_seconds)
    case_reports: list[dict[str, Any]] = []
    counts = {"stable": 0, "marginal": 0, "unstable": 0}

    for index, case in enumerate(cases, start=1):
        case_id = _case_identifier(case, index)
        state_spec = case["state_spec"] if isinstance(case, Mapping) and "state_spec" in case else case
        case_timeout = grid_timeout
        if isinstance(case, Mapping) and "timeout_seconds" in case:
            case_timeout = _normalize_timeout(case["timeout_seconds"])

        report = evaluate_structure(state_spec, timeout_seconds=case_timeout)
        counts[report["classification"]] += 1
        case_reports.append({"case_id": case_id, "report": report})

    return {
        "case_count": len(case_reports),
        "counts": counts,
        "cases": case_reports,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expose the frozen stability oracle as a bounded agent skill."
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a single state specification.",
    )
    evaluate_inputs = evaluate_parser.add_mutually_exclusive_group(required=True)
    evaluate_inputs.add_argument("--state-json", help="Inline JSON payload for a single state specification.")
    evaluate_inputs.add_argument("--state-file", type=Path, help="Path to a state-spec JSON file.")
    evaluate_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Hard timeout budget for the evaluation.",
    )
    evaluate_parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit a single-line JSON object for agent tool-calling.",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Evaluate a bounded batch of state specifications.",
    )
    scan_inputs = scan_parser.add_mutually_exclusive_group(required=True)
    scan_inputs.add_argument("--grid-json", help="Inline JSON payload for a scan grid.")
    scan_inputs.add_argument("--grid-file", type=Path, help="Path to a grid JSON file.")
    scan_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-case timeout budget for the scan.",
    )
    scan_parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit a single-line JSON object for agent tool-calling.",
    )

    schema_parser = subparsers.add_parser(
        "schema",
        help="Print the bundled tool schema.",
    )
    schema_parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit a single-line JSON object for agent tool-calling.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "evaluate":
            payload = _load_json_argument(args.state_json, args.state_file)
            result = evaluate_structure(payload, timeout_seconds=args.timeout_seconds)
            _emit_json(result, json_only=args.json_only)
            return

        if args.command == "scan":
            payload = _load_json_argument(args.grid_json, args.grid_file)
            result = scan_structure(payload, timeout_seconds=args.timeout_seconds)
            _emit_json(result, json_only=args.json_only)
            return

        if args.command == "schema":
            _emit_json(load_schema(), json_only=args.json_only)
            return

        raise SkillInputError(f"Unsupported command: {args.command}")
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        SkillInputError,
        SkillTimeoutError,
        TrajectoryValidationError,
        ValueError,
    ) as exc:
        raise SystemExit(str(exc)) from exc


def _evaluate_spec(spec: TrajectorySpec) -> ScanReport:
    return scan_trajectory(spec, include_recovery=False)


def _translate_report(scan_report: ScanReport) -> StabilityReport:
    propagation = scan_report.propagation
    persistence = scan_report.persistence
    ordering = scan_report.ordering

    classification = _map_classification(scan_report.classification.label)
    structural_retention = _bounded_round(
        (0.75 * persistence.mean_retention) + (0.25 * persistence.checkpoint_coverage)
    )
    temporal_consistency = _bounded_round(ordering.score / 100.0)

    if not ordering.is_acyclic:
        causal_deformation = 1.0
    else:
        causal_deformation = _bounded_round(
            (0.30 * propagation.irreversible_exposure)
            + (0.30 * propagation.pre_checkpoint_exposure)
            + (0.20 * (1.0 - propagation.connectivity_fraction))
            + (0.10 * propagation.branching_penalty)
            + (0.10 * (1.0 - temporal_consistency))
        )

    geometric_integrity = _bounded_round(
        (0.35 * propagation.reachable_fraction)
        + (0.25 * propagation.terminal_fraction)
        + (0.25 * propagation.connectivity_fraction)
        + (0.15 * (1.0 - propagation.branching_penalty))
    )

    return StabilityReport(
        classification=classification,
        structural_retention=structural_retention,
        temporal_consistency=temporal_consistency,
        causal_deformation=causal_deformation,
        geometric_integrity=geometric_integrity,
        summary=_build_summary(classification, scan_report.classification.reasons),
    )


def _map_classification(label: str) -> str:
    mapping = {
        "green": "stable",
        "yellow": "marginal",
        "red": "unstable",
    }
    try:
        return mapping[label]
    except KeyError as exc:
        raise SkillInputError(f"Unsupported oracle classification: {label}") from exc


def _build_summary(classification: str, reasons: Sequence[str]) -> str:
    detail = reasons[0] if reasons else "bounded stability signals are available"
    if classification == "stable":
        return f"Structure is stable with {detail}."
    return f"Structure is {classification} because {detail}."


def _coerce_state_spec(state_spec: Mapping[str, Any] | TrajectorySpec) -> TrajectorySpec:
    if isinstance(state_spec, TrajectorySpec):
        return state_spec
    if not isinstance(state_spec, Mapping):
        raise SkillInputError("state_spec must be a mapping or a TrajectorySpec.")
    return TrajectorySpec.from_dict(dict(state_spec))


def _coerce_cases(
    parameter_grid: Mapping[str, Any] | Sequence[Any],
    timeout_seconds: float | None,
) -> tuple[list[Any], float | None]:
    grid_timeout = _normalize_timeout(timeout_seconds)

    if isinstance(parameter_grid, Mapping):
        raw_cases = parameter_grid.get("cases")
        if raw_cases is None:
            raw_cases = [parameter_grid]
        grid_timeout = _normalize_timeout(parameter_grid.get("timeout_seconds", grid_timeout))
    elif isinstance(parameter_grid, Sequence) and not isinstance(parameter_grid, (str, bytes, bytearray)):
        raw_cases = list(parameter_grid)
    else:
        raise SkillInputError("parameter_grid must be a mapping with 'cases' or a sequence of cases.")

    if not isinstance(raw_cases, list) or not raw_cases:
        raise SkillInputError("scan_structure requires a non-empty 'cases' list.")
    return raw_cases, grid_timeout


def _case_identifier(case: Any, index: int) -> str:
    if isinstance(case, Mapping):
        if "case_id" in case:
            case_id = str(case["case_id"]).strip()
            if case_id:
                return case_id
        if "plan_id" in case:
            plan_id = str(case["plan_id"]).strip()
            if plan_id:
                return plan_id
        if "state_spec" in case and isinstance(case["state_spec"], Mapping):
            plan_id = str(case["state_spec"].get("plan_id", "")).strip()
            if plan_id:
                return plan_id
    return f"case-{index}"


def _normalize_timeout(timeout_seconds: Any) -> float | None:
    if timeout_seconds is None:
        return None
    timeout = float(timeout_seconds)
    if timeout <= 0.0:
        raise SkillInputError("timeout_seconds must be greater than zero.")
    return timeout


def _run_with_timeout(
    operation: Callable[[], ScanReport],
    timeout_seconds: float | None,
) -> ScanReport:
    start_time = time.monotonic()
    with _timeout_guard(timeout_seconds):
        result = operation()

    elapsed = time.monotonic() - start_time
    if timeout_seconds is not None and elapsed > timeout_seconds:
        raise SkillTimeoutError(
            f"stability evaluation exceeded timeout budget ({elapsed:.4f}s > {timeout_seconds:.4f}s)"
        )
    return result


@contextmanager
def _timeout_guard(timeout_seconds: float | None) -> Any:
    if (
        timeout_seconds is None
        or not hasattr(signal, "SIGALRM")
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)

    def _handle_timeout(signum: int, frame: Any) -> None:
        raise SkillTimeoutError(f"stability evaluation exceeded timeout budget ({timeout_seconds:.4f}s)")

    signal.signal(signal.SIGALRM, _handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)


def _load_json_argument(raw_json: str | None, path: Path | None) -> Any:
    if raw_json is not None:
        return json.loads(raw_json)
    if path is not None:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    raise SkillInputError("Expected either inline JSON or a JSON file path.")


def _emit_json(payload: Mapping[str, Any], json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=False))
        return
    print(json.dumps(payload, indent=2, sort_keys=False))


def _bounded_round(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


if __name__ == "__main__":
    main()
