from __future__ import annotations

import unittest

from haos_skill import OracleResult, Perturbation, StabilityMetrics, State


class StateSpecTests(unittest.TestCase):
    def test_state_round_trip_normalizes_json_friendly_shape(self) -> None:
        state = State.from_dict(
            {
                "nodes": [1, "2"],
                "edges": [[1, "2"]],
                "features": {"1": {"kind": "root"}},
                "timestamps": {"2": 1.5},
            }
        )

        self.assertEqual(state.nodes, (1, 2))
        self.assertEqual(state.edges, ((1, 2),))
        self.assertEqual(
            state.to_dict(),
            {
                "nodes": [1, 2],
                "edges": [[1, 2]],
                "features": {"1": {"kind": "root"}},
                "timestamps": {"2": 1.5},
            },
        )

    def test_state_rejects_unknown_edge_endpoint(self) -> None:
        with self.assertRaises(ValueError):
            State(nodes=(1,), edges=((1, 2),))

    def test_oracle_result_round_trip_is_typed_and_bounded(self) -> None:
        result = OracleResult(
            classification="stable",
            metrics=StabilityMetrics(
                structural_retention=0.9,
                temporal_consistency=0.8,
                causal_deformation=0.1,
                geometric_integrity=0.85,
            ),
            confidence=0.72,
            coherence_score=0.8375,
            metric_vector={
                "structural_retention": 0.9,
                "temporal_consistency": 0.8,
                "causal_deformation": 0.1,
                "geometric_integrity": 0.85,
            },
            normalized_vector={
                "structural_retention": 0.9,
                "temporal_consistency": 0.8,
                "causal_stability": 0.9,
                "geometric_integrity": 0.85,
            },
            policy_version="v1_floor_mean_band",
            trace={
                "input_node_count": 4,
                "input_edge_count": 3,
                "output_node_count": 4,
                "output_edge_count": 3,
                "normalized_vector": {
                    "structural_retention": 0.9,
                    "temporal_consistency": 0.8,
                    "causal_stability": 0.9,
                    "geometric_integrity": 0.85,
                },
                "coherence_score": 0.8375,
                "spread": 0.1,
                "floor_triggered": False,
                "policy_version": "v1_floor_mean_band",
            },
        )

        self.assertEqual(
            OracleResult.from_dict(result.to_dict()).to_dict(),
            {
                "classification": "stable",
                "metrics": {
                    "structural_retention": 0.9,
                    "temporal_consistency": 0.8,
                    "causal_deformation": 0.1,
                    "geometric_integrity": 0.85,
                },
                "confidence": 0.72,
                "coherence_score": 0.8375,
                "metric_vector": {
                    "structural_retention": 0.9,
                    "temporal_consistency": 0.8,
                    "causal_deformation": 0.1,
                    "geometric_integrity": 0.85,
                },
                "normalized_vector": {
                    "structural_retention": 0.9,
                    "temporal_consistency": 0.8,
                    "causal_stability": 0.9,
                    "geometric_integrity": 0.85,
                },
                "policy_version": "v1_floor_mean_band",
                "trace": {
                    "input_node_count": 4,
                    "input_edge_count": 3,
                    "output_node_count": 4,
                    "output_edge_count": 3,
                    "normalized_vector": {
                        "structural_retention": 0.9,
                        "temporal_consistency": 0.8,
                        "causal_stability": 0.9,
                        "geometric_integrity": 0.85,
                    },
                    "coherence_score": 0.8375,
                    "spread": 0.1,
                    "floor_triggered": False,
                    "policy_version": "v1_floor_mean_band",
                },
            },
        )

    def test_perturbation_normalizes_values(self) -> None:
        perturbation = Perturbation(node_drop=0.25, edge_drop=0.1, noise=0.05, cluster_split=1)

        self.assertEqual(
            perturbation.to_dict(),
            {
                "node_drop": 0.25,
                "edge_drop": 0.1,
                "noise": 0.05,
                "cluster_split": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
