from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .trajectory import TrajectorySpec


@dataclass(frozen=True)
class PersistenceMetrics:
    score: float
    mean_retention: float
    checkpoint_coverage: float
    tracked_edges: int
    broken_edges: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_persistence_metrics(spec: TrajectorySpec) -> PersistenceMetrics:
    node_map = spec.node_map()
    if not spec.edges:
        return PersistenceMetrics(
            score=100.0,
            mean_retention=1.0,
            checkpoint_coverage=1.0,
            tracked_edges=0,
            broken_edges=(),
        )

    retention_values: list[float] = []
    broken_edges: list[str] = []

    for edge in spec.edges:
        source = node_map[edge.source]
        target = node_map[edge.target]

        source_tags = set(source.invariant_tags)
        target_tags = set(target.invariant_tags)

        if not source_tags:
            retention = 1.0
        else:
            retention = len(source_tags & target_tags) / len(source_tags)

        if retention == 0.0 and source_tags:
            broken_edges.append(f"{edge.source}->{edge.target}")
        retention_values.append(retention)

    checkpoints = [node for node in spec.nodes if node.checkpoint]
    if checkpoints:
        checkpoint_coverage = sum(1 for node in checkpoints if node.invariant_tags) / len(checkpoints)
    else:
        checkpoint_coverage = 0.0

    mean_retention = sum(retention_values) / len(retention_values)
    score = 100.0 * ((0.75 * mean_retention) + (0.25 * checkpoint_coverage))

    return PersistenceMetrics(
        score=round(score, 2),
        mean_retention=round(mean_retention, 4),
        checkpoint_coverage=round(checkpoint_coverage, 4),
        tracked_edges=len(retention_values),
        broken_edges=tuple(broken_edges),
    )
