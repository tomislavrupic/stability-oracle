from __future__ import annotations

import unittest

from haos_skill.metrics import (
    CausalDeformationMetric,
    GeometricIntegrityMetric,
    MetricRegistry,
    StructuralRetentionMetric,
    TemporalConsistencyMetric,
)
from haos_skill.state_spec import State


class MetricInterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = State(
            nodes=(1, 2, 3),
            edges=((1, 2), (2, 3)),
            timestamps={1: 0.0, 2: 1.0, 3: 2.0},
        )
        self.after = State(
            nodes=(1, 2),
            edges=((1, 2),),
            timestamps={1: 0.0, 2: 1.0},
        )

    def test_registry_computes_all_metrics(self) -> None:
        registry = MetricRegistry(
            [
                StructuralRetentionMetric(),
                TemporalConsistencyMetric(),
                CausalDeformationMetric(),
                GeometricIntegrityMetric(),
            ]
        )

        result = registry.compute_all(self.before, self.after)

        self.assertEqual(
            tuple(result),
            (
                "structural_retention",
                "temporal_consistency",
                "causal_deformation",
                "geometric_integrity",
            ),
        )
        for value in result.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_structural_retention_uses_shared_nodes(self) -> None:
        metric = StructuralRetentionMetric()
        self.assertEqual(metric.compute(self.before, self.after), 2 / 3)

    def test_temporal_consistency_tracks_order_preservation(self) -> None:
        metric = TemporalConsistencyMetric()
        reordered = State(
            nodes=(1, 2, 3),
            edges=((1, 2), (2, 3)),
            timestamps={1: 2.0, 2: 1.0, 3: 0.0},
        )

        self.assertEqual(metric.compute(self.before, self.after), 1.0)
        self.assertEqual(metric.compute(self.before, reordered), 0.0)

    def test_causal_deformation_grows_with_edge_change(self) -> None:
        metric = CausalDeformationMetric()
        expanded = State(
            nodes=(1, 2, 3),
            edges=((1, 2), (2, 3), (1, 3)),
        )

        self.assertEqual(metric.compute(self.before, self.before), 0.0)
        self.assertGreater(metric.compute(self.before, self.after), 0.0)
        self.assertGreater(metric.compute(self.before, expanded), 0.0)

    def test_geometric_integrity_preserves_local_adjacency(self) -> None:
        metric = GeometricIntegrityMetric()
        disconnected = State(nodes=(1, 2, 3), edges=())

        self.assertEqual(metric.compute(self.before, self.before), 1.0)
        self.assertEqual(metric.compute(self.before, disconnected), 0.0)


if __name__ == "__main__":
    unittest.main()
