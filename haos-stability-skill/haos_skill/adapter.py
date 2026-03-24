from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import shlex
import subprocess
from typing import Any, Mapping, Optional, Sequence, Tuple

from .safety import (
    OracleExecutionError,
    OracleProtocolError,
    SkillTimeoutError,
    bounded_round,
    canonical_json,
    coerce_unit_interval,
    normalize_timeout,
)


DEFAULT_ORACLE_COMMAND = ("haos_iip.demo", "stability", "--json")
ORACLE_COMMAND_ENV = "HAOS_ORACLE_COMMAND"


@dataclass(frozen=True)
class NormalizedOracleMetrics:
    structural_retention: float
    temporal_consistency: float
    causal_deformation: float
    geometric_integrity: float
    classification_hint: Optional[str] = None
    primary_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_oracle_command(command: Optional[Sequence[str]] = None) -> Tuple[str, ...]:
    if command:
        return tuple(command)

    raw_env_command = os.environ.get(ORACLE_COMMAND_ENV, "").strip()
    if raw_env_command:
        parsed = tuple(shlex.split(raw_env_command))
        if parsed:
            return parsed

    return DEFAULT_ORACLE_COMMAND


def run_stability_oracle(
    state_spec: Mapping[str, Any],
    timeout: float = 2.0,
    command: Optional[Sequence[str]] = None,
) -> NormalizedOracleMetrics:
    resolved_timeout = normalize_timeout(timeout)
    resolved_command = resolve_oracle_command(command)
    state_json = canonical_json(state_spec)
    argv, stdin_payload = _build_invocation(resolved_command, state_json)

    try:
        completed = subprocess.run(
            argv,
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillTimeoutError(
            "external HAOS oracle exceeded timeout budget of %.2fs" % resolved_timeout
        ) from exc
    except FileNotFoundError as exc:
        raise OracleExecutionError(
            "external HAOS oracle command not found: %s" % " ".join(resolved_command)
        ) from exc
    except OSError as exc:
        raise OracleExecutionError("failed to execute external HAOS oracle") from exc

    if completed.returncode != 0:
        stderr_text = (completed.stderr or "").strip()
        raise OracleExecutionError(
            "external HAOS oracle failed with code %d%s"
            % (completed.returncode, ": %s" % stderr_text if stderr_text else "")
        )

    stdout_text = (completed.stdout or "").strip()
    if not stdout_text:
        raise OracleProtocolError("external HAOS oracle returned empty stdout")

    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise OracleProtocolError("external HAOS oracle returned invalid JSON") from exc

    if not isinstance(payload, Mapping):
        raise OracleProtocolError("external HAOS oracle must return a JSON object")

    return normalize_oracle_payload(payload)


def normalize_oracle_payload(payload: Mapping[str, Any]) -> NormalizedOracleMetrics:
    direct = _normalize_direct_metrics(payload, payload)
    if direct is not None:
        return direct

    metrics_payload = payload.get("metrics")
    if isinstance(metrics_payload, Mapping):
        direct = _normalize_direct_metrics(metrics_payload, payload)
        if direct is not None:
            return direct

    if (
        isinstance(payload.get("propagation"), Mapping)
        and isinstance(payload.get("persistence"), Mapping)
        and isinstance(payload.get("ordering"), Mapping)
    ):
        return _normalize_nested_oracle_payload(payload)

    raise OracleProtocolError("external HAOS oracle payload did not match a supported schema")


def _build_invocation(command: Sequence[str], state_json: str) -> Tuple[list[str], Optional[str]]:
    if any("{state_json}" in part for part in command):
        argv = [part.replace("{state_json}", state_json) for part in command]
        return argv, None

    if "--state-json" in command:
        return list(command) + [state_json], None

    return list(command), state_json


def _normalize_direct_metrics(
    metrics_payload: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> Optional[NormalizedOracleMetrics]:
    required_fields = (
        "structural_retention",
        "temporal_consistency",
        "causal_deformation",
        "geometric_integrity",
    )
    if not all(field in metrics_payload for field in required_fields):
        return None

    return NormalizedOracleMetrics(
        structural_retention=coerce_unit_interval(
            metrics_payload["structural_retention"], "structural_retention"
        ),
        temporal_consistency=coerce_unit_interval(
            metrics_payload["temporal_consistency"], "temporal_consistency"
        ),
        causal_deformation=coerce_unit_interval(
            metrics_payload["causal_deformation"], "causal_deformation"
        ),
        geometric_integrity=coerce_unit_interval(
            metrics_payload["geometric_integrity"], "geometric_integrity"
        ),
        classification_hint=_extract_classification_hint(envelope),
        primary_reason=_extract_primary_reason(envelope),
    )


def _normalize_nested_oracle_payload(payload: Mapping[str, Any]) -> NormalizedOracleMetrics:
    propagation = payload["propagation"]
    persistence = payload["persistence"]
    ordering = payload["ordering"]

    if not isinstance(propagation, Mapping) or not isinstance(persistence, Mapping) or not isinstance(
        ordering, Mapping
    ):
        raise OracleProtocolError("external HAOS oracle nested metrics must be JSON objects")

    structural_retention = bounded_round(
        (0.75 * coerce_unit_interval(persistence.get("mean_retention"), "mean_retention"))
        + (0.25 * coerce_unit_interval(persistence.get("checkpoint_coverage"), "checkpoint_coverage"))
    )
    temporal_consistency = coerce_unit_interval(ordering.get("score"), "ordering.score")

    is_acyclic = bool(ordering.get("is_acyclic", True))
    if not is_acyclic:
        causal_deformation = 1.0
    else:
        causal_deformation = bounded_round(
            (0.30 * coerce_unit_interval(propagation.get("irreversible_exposure"), "irreversible_exposure"))
            + (
                0.30
                * coerce_unit_interval(
                    propagation.get("pre_checkpoint_exposure"),
                    "pre_checkpoint_exposure",
                )
            )
            + (
                0.20
                * (
                    1.0
                    - coerce_unit_interval(
                        propagation.get("connectivity_fraction"),
                        "connectivity_fraction",
                    )
                )
            )
            + (0.10 * coerce_unit_interval(propagation.get("branching_penalty"), "branching_penalty"))
            + (0.10 * (1.0 - temporal_consistency))
        )

    geometric_integrity = bounded_round(
        (0.35 * coerce_unit_interval(propagation.get("reachable_fraction"), "reachable_fraction"))
        + (0.25 * coerce_unit_interval(propagation.get("terminal_fraction"), "terminal_fraction"))
        + (0.25 * coerce_unit_interval(propagation.get("connectivity_fraction"), "connectivity_fraction"))
        + (
            0.15
            * (
                1.0 - coerce_unit_interval(propagation.get("branching_penalty"), "branching_penalty")
            )
        )
    )

    return NormalizedOracleMetrics(
        structural_retention=structural_retention,
        temporal_consistency=temporal_consistency,
        causal_deformation=causal_deformation,
        geometric_integrity=geometric_integrity,
        classification_hint=_extract_classification_hint(payload),
        primary_reason=_extract_primary_reason(payload),
    )


def _extract_classification_hint(payload: Mapping[str, Any]) -> Optional[str]:
    raw_classification = payload.get("classification")
    if isinstance(raw_classification, Mapping):
        raw_classification = raw_classification.get("label")
    if raw_classification is None:
        raw_classification = payload.get("label")
    if raw_classification is None:
        return None

    normalized = str(raw_classification).strip().lower()
    mapping = {
        "green": "stable",
        "yellow": "marginal",
        "red": "unstable",
        "stable": "stable",
        "marginal": "marginal",
        "unstable": "unstable",
    }
    if normalized not in mapping:
        raise OracleProtocolError("unsupported external classification: %s" % raw_classification)
    return mapping[normalized]


def _extract_primary_reason(payload: Mapping[str, Any]) -> Optional[str]:
    summary = payload.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    reason = payload.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()

    classification = payload.get("classification")
    if isinstance(classification, Mapping):
        reasons = classification.get("reasons")
        if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes, bytearray)):
            for entry in reasons:
                if isinstance(entry, str) and entry.strip():
                    return entry.strip()
    return None
