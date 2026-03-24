from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .metrics_propagation import compute_propagation_metrics
from .perturbations import drop_node
from .trajectory import TrajectorySpec, TrajectoryValidationError


@dataclass(frozen=True)
class RecoveryMetrics:
    score: float
    evaluated_drop_count: int
    mean_perturbed_propagation: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_recovery_metrics(spec: TrajectorySpec) -> RecoveryMetrics:
    candidate_nodes = [node for node in spec.nodes if not node.checkpoint]
    if not candidate_nodes:
        return RecoveryMetrics(score=100.0, evaluated_drop_count=0, mean_perturbed_propagation=100.0)

    propagation_scores: list[float] = []
    for node in candidate_nodes:
        try:
            perturbed = drop_node(spec, node.id, reconnect=node.reversible)
            propagation_scores.append(compute_propagation_metrics(perturbed).score)
        except (TrajectoryValidationError, ValueError):
            propagation_scores.append(0.0)

    mean_perturbed_propagation = sum(propagation_scores) / len(propagation_scores)
    baseline = compute_propagation_metrics(spec).score or 1.0
    score = min(100.0, 100.0 * (mean_perturbed_propagation / baseline))

    return RecoveryMetrics(
        score=round(score, 2),
        evaluated_drop_count=len(candidate_nodes),
        mean_perturbed_propagation=round(mean_perturbed_propagation, 2),
    )
