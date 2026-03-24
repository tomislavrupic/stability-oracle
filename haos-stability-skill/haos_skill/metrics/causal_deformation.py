from __future__ import annotations

from .base import StabilityMetric
from ..state_spec import State


class CausalDeformationMetric(StabilityMetric):
    name = "causal_deformation"

    def compute(self, before: State, after: State) -> float:
        before_edges = set(before.edges)
        after_edges = set(after.edges)

        if not before_edges:
            return 0.0 if not after_edges else 1.0

        removed_fraction = len(before_edges - after_edges) / len(before_edges)
        added_fraction = len(after_edges - before_edges) / max(len(before_edges), 1)
        deformation = 0.7 * removed_fraction + 0.3 * min(1.0, added_fraction)
        return min(1.0, deformation)
