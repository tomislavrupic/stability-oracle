from __future__ import annotations

from itertools import combinations

from .base import StabilityMetric
from ..state_spec import State


class TemporalConsistencyMetric(StabilityMetric):
    name = "temporal_consistency"

    def compute(self, before: State, after: State) -> float:
        if before.timestamps is None or after.timestamps is None:
            return 1.0

        shared_nodes = sorted(set(before.timestamps) & set(after.timestamps))
        if len(shared_nodes) < 2:
            return 1.0

        consistent_pairs = 0
        compared_pairs = 0
        for left, right in combinations(shared_nodes, 2):
            before_delta = before.timestamps[left] - before.timestamps[right]
            after_delta = after.timestamps[left] - after.timestamps[right]
            if before_delta == 0.0 and after_delta == 0.0:
                consistent_pairs += 1
            elif before_delta == 0.0 or after_delta == 0.0:
                compared_pairs += 1
                continue
            elif before_delta * after_delta > 0.0:
                consistent_pairs += 1
            compared_pairs += 1

        if compared_pairs == 0:
            return 1.0
        return consistent_pairs / compared_pairs
