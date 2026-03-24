from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..state_spec import OracleResult, StabilityMetrics


POLICY_VERSION_V1 = "v1_floor_mean_band"


@dataclass(frozen=True)
class PolicyConfig:
    floor_threshold: float = 0.30
    stable_coherence_threshold: float = 0.75
    stable_spread_threshold: float = 0.35
    marginal_coherence_threshold: float = 0.50
    policy_version: str = POLICY_VERSION_V1

    @classmethod
    def strict(cls) -> "PolicyConfig":
        return cls(
            floor_threshold=0.40,
            stable_coherence_threshold=0.82,
            stable_spread_threshold=0.25,
            marginal_coherence_threshold=0.60,
            policy_version="v1_strict_floor_mean_band",
        )

    @classmethod
    def balanced(cls) -> "PolicyConfig":
        return cls()

    @classmethod
    def exploratory(cls) -> "PolicyConfig":
        return cls(
            floor_threshold=0.20,
            stable_coherence_threshold=0.70,
            stable_spread_threshold=0.45,
            marginal_coherence_threshold=0.45,
            policy_version="v1_exploratory_floor_mean_band",
        )

    def __post_init__(self) -> None:
        for field_name in (
            "floor_threshold",
            "stable_coherence_threshold",
            "stable_spread_threshold",
            "marginal_coherence_threshold",
        ):
            value = round(float(getattr(self, field_name)), 4)
            if not 0.0 <= value <= 1.0:
                raise ValueError("%s must be within [0.0, 1.0]" % field_name)
            object.__setattr__(self, field_name, value)

        if self.marginal_coherence_threshold > self.stable_coherence_threshold:
            raise ValueError("marginal_coherence_threshold must not exceed stable_coherence_threshold")
        if not str(self.policy_version).strip():
            raise ValueError("policy_version must be a non-empty string")


class StabilityClassifier:
    """
    Deterministic policy module that maps metric signals to a bounded verdict.
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def evaluate(self, metrics: StabilityMetrics) -> OracleResult:
        metric_vector = metrics.to_dict()
        normalized_vector = self.normalize(metrics)
        values = tuple(normalized_vector.values())

        minimum = min(values)
        coherence = _mean(values)
        spread = max(values) - minimum

        if minimum < self.config.floor_threshold:
            classification = "unstable"
        elif (
            coherence >= self.config.stable_coherence_threshold
            and spread <= self.config.stable_spread_threshold
        ):
            classification = "stable"
        elif (
            coherence >= self.config.marginal_coherence_threshold
            and minimum >= self.config.floor_threshold
        ):
            classification = "marginal"
        else:
            classification = "unstable"

        confidence = _bounded_round(coherence * (1.0 - spread))

        return OracleResult(
            classification=classification,
            metrics=metrics,
            confidence=confidence,
            coherence_score=_bounded_round(coherence),
            metric_vector=metric_vector,
            normalized_vector=normalized_vector,
            policy_version=self.config.policy_version,
        )

    def normalize(self, metrics: StabilityMetrics) -> Dict[str, float]:
        return {
            "structural_retention": metrics.structural_retention,
            "temporal_consistency": metrics.temporal_consistency,
            "causal_stability": _bounded_round(1.0 - metrics.causal_deformation),
            "geometric_integrity": metrics.geometric_integrity,
        }


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values)


def _bounded_round(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
