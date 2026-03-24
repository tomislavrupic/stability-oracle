from __future__ import annotations

from typing import Sequence

from ..metrics import MetricRegistry, build_default_metric_registry
from ..perturbations import PerturbationEngine
from ..safety import bounded_round
from ..state_spec import OracleResult, Perturbation, StabilityMetrics, State, coerce_perturbation, coerce_state
from .classifier import PolicyConfig, StabilityClassifier
from .exceptions import OraclePerturbationError, OracleStateValidationError


class OracleEngine:
    def __init__(
        self,
        registry: MetricRegistry,
        classifier: StabilityClassifier,
        perturbation_engine: PerturbationEngine | None = None,
    ) -> None:
        self.registry = registry
        self.classifier = classifier
        self.perturbation_engine = perturbation_engine or PerturbationEngine()

    def evaluate_transition(
        self,
        before: State,
        after: State,
    ) -> OracleResult:
        before_state = _coerce_state_or_raise(before)
        after_state = _coerce_state_or_raise(after)

        metric_values = self.registry.compute_all(before_state, after_state)
        try:
            metrics = StabilityMetrics(**metric_values)
        except TypeError as exc:
            raise OracleStateValidationError(
                "metric registry must produce structural_retention, temporal_consistency, causal_deformation, and geometric_integrity"
            ) from exc

        result = self.classifier.evaluate(metrics)
        return OracleResult(
            classification=result.classification,
            metrics=result.metrics,
            confidence=result.confidence,
            coherence_score=result.coherence_score,
            metric_vector=dict(result.metric_vector),
            normalized_vector=dict(result.normalized_vector),
            policy_version=result.policy_version,
            trace=_build_trace_payload(
                before_state=before_state,
                after_state=after_state,
                result=result,
                floor_threshold=self.classifier.config.floor_threshold,
            ),
        )

    def evaluate(
        self,
        before: State,
        perturbation: Perturbation,
    ) -> OracleResult:
        before_state = _coerce_state_or_raise(before)
        perturbation_spec = _coerce_perturbation_or_raise(perturbation)
        after_state = self.perturbation_engine.apply(before_state, perturbation_spec)
        return self.evaluate_transition(before_state, after_state)

    def scan(
        self,
        before: State,
        perturbations: list[Perturbation],
    ) -> list[OracleResult]:
        before_state = _coerce_state_or_raise(before)
        if not isinstance(perturbations, Sequence) or isinstance(perturbations, (str, bytes, bytearray)):
            raise OraclePerturbationError("perturbations must be a sequence")
        normalized = [_coerce_perturbation_or_raise(item) for item in perturbations]
        return [self.evaluate(before_state, perturbation) for perturbation in normalized]


def build_default_engine(config: PolicyConfig | None = None) -> OracleEngine:
    classifier = StabilityClassifier(config or PolicyConfig.balanced())
    return OracleEngine(
        registry=build_default_metric_registry(),
        classifier=classifier,
        perturbation_engine=PerturbationEngine(),
    )


def _coerce_state_or_raise(value: State) -> State:
    try:
        return coerce_state(value)
    except (TypeError, ValueError) as exc:
        raise OracleStateValidationError("invalid state payload") from exc


def _coerce_perturbation_or_raise(value: Perturbation) -> Perturbation:
    try:
        return coerce_perturbation(value)
    except (TypeError, ValueError) as exc:
        raise OraclePerturbationError("invalid perturbation payload") from exc


def _build_trace_payload(
    before_state: State,
    after_state: State,
    result: OracleResult,
    floor_threshold: float,
) -> dict[str, object]:
    values = tuple(result.normalized_vector.values())
    minimum = min(values)
    spread = bounded_round(max(values) - minimum)
    return {
        "input_node_count": len(before_state.nodes),
        "input_edge_count": len(before_state.edges),
        "output_node_count": len(after_state.nodes),
        "output_edge_count": len(after_state.edges),
        "normalized_vector": dict(result.normalized_vector),
        "coherence_score": result.coherence_score,
        "spread": spread,
        "floor_triggered": minimum < floor_threshold,
        "policy_version": result.policy_version,
    }
