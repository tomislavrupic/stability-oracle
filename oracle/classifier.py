from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .metrics_ordering import OrderingMetrics
from .metrics_persistence import PersistenceMetrics
from .metrics_propagation import PropagationMetrics
from .trajectory import TrajectorySpec


@dataclass(frozen=True)
class StabilityClassification:
    label: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_trajectory(
    spec: TrajectorySpec,
    propagation: PropagationMetrics,
    persistence: PersistenceMetrics,
    ordering: OrderingMetrics,
) -> StabilityClassification:
    reasons: list[str] = []

    if not ordering.is_acyclic:
        reasons.append("ordering cycle detected")
        return StabilityClassification(label="red", reasons=tuple(reasons))

    if propagation.pre_checkpoint_exposure >= 0.55:
        reasons.append("high irreversible exposure before first checkpoint")
    if propagation.score < 70.0:
        reasons.append("weak propagation score")
    if persistence.mean_retention < 0.4:
        reasons.append("invariants collapse across transitions")
    if spec.checkpoint_count() == 0:
        reasons.append("missing checkpoints")

    if reasons:
        return StabilityClassification(label="red", reasons=tuple(reasons))

    warnings: list[str] = []
    if propagation.score < 85.0:
        warnings.append("propagation is serviceable but not robust")
    if persistence.score < 80.0:
        warnings.append("persistence is partial")
    if ordering.score < 90.0:
        warnings.append("ordering has extra fan-in or fan-out")
    if spec.checkpoint_count() == 1:
        warnings.append("single checkpoint leaves narrow recovery margin")

    if warnings:
        return StabilityClassification(label="yellow", reasons=tuple(warnings))

    return StabilityClassification(label="green", reasons=("clean propagation and retained invariants",))
