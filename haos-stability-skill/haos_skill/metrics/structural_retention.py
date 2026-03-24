from __future__ import annotations

from .base import StabilityMetric
from ..state_spec import State


class StructuralRetentionMetric(StabilityMetric):
    name = "structural_retention"

    def compute(self, before: State, after: State) -> float:
        if not before.nodes:
            return 1.0

        retained = len(set(before.nodes) & set(after.nodes))
        return retained / len(before.nodes)
