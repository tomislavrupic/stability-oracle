from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classifier import StabilityClassification, classify_trajectory
from .metrics_ordering import OrderingMetrics, compute_ordering_metrics
from .metrics_persistence import PersistenceMetrics, compute_persistence_metrics
from .metrics_propagation import PropagationMetrics, compute_propagation_metrics
from .metrics_recovery import RecoveryMetrics, compute_recovery_metrics
from .trajectory import TrajectorySpec


@dataclass(frozen=True)
class ScanReport:
    plan_id: str
    propagation: PropagationMetrics
    persistence: PersistenceMetrics
    ordering: OrderingMetrics
    classification: StabilityClassification
    recovery: RecoveryMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "propagation": self.propagation.to_dict(),
            "persistence": self.persistence.to_dict(),
            "ordering": self.ordering.to_dict(),
            "classification": self.classification.to_dict(),
            "recovery": self.recovery.to_dict() if self.recovery else None,
        }

    def render_text(self) -> str:
        lines = [
            f"plan_id: {self.plan_id}",
            f"classification: {self.classification.label}",
            f"propagation_score: {self.propagation.score}",
            f"persistence_score: {self.persistence.score}",
            f"ordering_score: {self.ordering.score}",
        ]

        if self.recovery:
            lines.append(f"recovery_score: {self.recovery.score}")

        lines.append("reasons:")
        for reason in self.classification.reasons:
            lines.append(f"- {reason}")

        return "\n".join(lines)


def scan_trajectory(spec: TrajectorySpec, include_recovery: bool = False) -> ScanReport:
    propagation = compute_propagation_metrics(spec)
    persistence = compute_persistence_metrics(spec)
    ordering = compute_ordering_metrics(spec)
    classification = classify_trajectory(spec, propagation, persistence, ordering)
    recovery = compute_recovery_metrics(spec) if include_recovery else None

    return ScanReport(
        plan_id=spec.plan_id,
        propagation=propagation,
        persistence=persistence,
        ordering=ordering,
        classification=classification,
        recovery=recovery,
    )
