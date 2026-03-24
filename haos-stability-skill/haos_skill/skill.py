from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.resources import files
import json
from typing import Any, Mapping, Optional, Sequence

from .adapter import NormalizedOracleMetrics, resolve_oracle_command, run_stability_oracle
from .cache import CacheProtocol
from .oracle import StabilityClassifier
from .safety import (
    DEFAULT_TIMEOUT_SECONDS,
    bounded_round,
    coerce_scan_cases,
    deep_copy_json_object,
    ensure_state_spec_limits,
    normalize_timeout,
)
from .state_spec import StabilityMetrics


@dataclass(frozen=True)
class StabilityReport:
    classification: str
    structural_retention: float
    temporal_consistency: float
    causal_deformation: float
    geometric_integrity: float
    confidence: float
    coherence_score: float
    metric_vector: dict[str, float]
    normalized_vector: dict[str, float]
    policy_version: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CLASSIFIER = StabilityClassifier()


def load_schema() -> dict[str, Any]:
    schema_path = files("haos_skill").joinpath("schema.json")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def evaluate_structure(
    state_spec: Mapping[str, Any],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    cache: Optional[CacheProtocol] = None,
    oracle_command: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    ensure_state_spec_limits(state_spec)
    normalized_timeout = normalize_timeout(timeout)
    cache_key_payload = {
        "command": list(resolve_oracle_command(oracle_command)),
        "state_spec": dict(state_spec),
    }

    if cache is not None:
        cached = cache.get("evaluate_structure", cache_key_payload)
        if cached is not None:
            return cached

    metrics = run_stability_oracle(
        state_spec=state_spec,
        timeout=normalized_timeout,
        command=oracle_command,
    )
    report = _build_report(metrics)
    report_dict = report.to_dict()

    if cache is not None:
        cache.set("evaluate_structure", cache_key_payload, report_dict)

    return report_dict


def scan_structure(
    grid_spec: Any,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    cache: Optional[CacheProtocol] = None,
    oracle_command: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    normalized_timeout = normalize_timeout(timeout)
    cases = coerce_scan_cases(grid_spec)

    case_reports = []
    counts = {"stable": 0, "marginal": 0, "unstable": 0}

    for index, case in enumerate(cases, start=1):
        case_id = _resolve_case_id(case, index)
        case_timeout = normalize_timeout(case.get("timeout", normalized_timeout))
        state_spec = case["state_spec"]
        report = evaluate_structure(
            state_spec=state_spec,
            timeout=case_timeout,
            cache=cache,
            oracle_command=oracle_command,
        )
        counts[report["classification"]] += 1
        case_reports.append({"case_id": case_id, "report": deep_copy_json_object(report)})

    return {
        "case_count": len(case_reports),
        "counts": counts,
        "cases": case_reports,
    }


def _build_report(metrics: NormalizedOracleMetrics) -> StabilityReport:
    raw_metrics = StabilityMetrics(
        structural_retention=metrics.structural_retention,
        temporal_consistency=metrics.temporal_consistency,
        causal_deformation=metrics.causal_deformation,
        geometric_integrity=metrics.geometric_integrity,
    )
    policy_result = DEFAULT_CLASSIFIER.evaluate(raw_metrics)
    return StabilityReport(
        classification=policy_result.classification,
        structural_retention=bounded_round(raw_metrics.structural_retention),
        temporal_consistency=bounded_round(raw_metrics.temporal_consistency),
        causal_deformation=bounded_round(raw_metrics.causal_deformation),
        geometric_integrity=bounded_round(raw_metrics.geometric_integrity),
        confidence=policy_result.confidence,
        coherence_score=policy_result.coherence_score,
        metric_vector=dict(policy_result.metric_vector),
        normalized_vector=dict(policy_result.normalized_vector),
        policy_version=policy_result.policy_version,
        summary=_build_summary(policy_result.classification, metrics),
    )


def _build_summary(classification: str, metrics: NormalizedOracleMetrics) -> str:
    if metrics.primary_reason:
        reason = metrics.primary_reason.rstrip(".")
        if reason.lower().startswith("structure is "):
            return reason + "."
        if classification == "stable":
            return "Structure is stable with %s." % reason
        return "Structure is %s because %s." % (classification, reason)

    if classification == "stable":
        return "Structure is stable with high retention and low deformation."
    if classification == "marginal":
        return "Structure is marginal because recovery signals are mixed."
    return "Structure is unstable because recoverable coherence breaks under current loading."


def _resolve_case_id(case: Mapping[str, Any], index: int) -> str:
    raw_case_id = case.get("case_id")
    if isinstance(raw_case_id, str) and raw_case_id.strip():
        return raw_case_id.strip()

    state_spec = case.get("state_spec")
    if isinstance(state_spec, Mapping):
        plan_id = state_spec.get("plan_id")
        if isinstance(plan_id, str) and plan_id.strip():
            return plan_id.strip()

    return "case-%d" % index
