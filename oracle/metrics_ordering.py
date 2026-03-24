from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .trajectory import TrajectorySpec


@dataclass(frozen=True)
class OrderingMetrics:
    score: float
    is_acyclic: bool
    root_count: int
    sink_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_ordering_metrics(spec: TrajectorySpec) -> OrderingMetrics:
    topological_order = spec.topological_order()
    is_acyclic = topological_order is not None
    root_count = len(spec.roots())
    sink_count = len(spec.sinks())

    score = 100.0 if is_acyclic else 0.0
    if is_acyclic and root_count > 1:
        score -= min(20.0, 5.0 * (root_count - 1))
    if is_acyclic and sink_count > 1:
        score -= min(15.0, 5.0 * (sink_count - 1))

    return OrderingMetrics(
        score=round(max(0.0, score), 2),
        is_acyclic=is_acyclic,
        root_count=root_count,
        sink_count=sink_count,
    )
