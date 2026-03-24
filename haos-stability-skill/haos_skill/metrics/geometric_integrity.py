from __future__ import annotations

from .base import StabilityMetric
from ..state_spec import State


class GeometricIntegrityMetric(StabilityMetric):
    name = "geometric_integrity"

    def compute(self, before: State, after: State) -> float:
        before_nodes = set(before.nodes)
        after_nodes = set(after.nodes)
        shared_nodes = before_nodes & after_nodes

        if not before_nodes:
            return 1.0
        if not shared_nodes:
            return 0.0

        before_local_edges = {
            edge for edge in before.edges if edge[0] in shared_nodes and edge[1] in shared_nodes
        }
        after_local_edges = {
            edge for edge in after.edges if edge[0] in shared_nodes and edge[1] in shared_nodes
        }

        if not before_local_edges:
            return 1.0

        preserved_local_edges = len(before_local_edges & after_local_edges)
        return preserved_local_edges / len(before_local_edges)
