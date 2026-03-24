from __future__ import annotations

import unittest

from haos_skill import Perturbation, State, build_default_engine, explain_result
from haos_skill.oracle import OraclePerturbationError, OracleStateValidationError
from haos_skill.perturbations import PerturbationEngine


BASE_STATE = State(
    nodes=(1, 2, 3, 4),
    edges=((1, 2), (2, 3), (3, 4)),
    features={4: {"kind": "sink"}},
    timestamps={1: 0.0, 2: 1.0, 3: 2.0, 4: 3.0},
)


class PerturbationEngineTests(unittest.TestCase):
    def test_apply_returns_new_state_without_mutating_input(self) -> None:
        engine = PerturbationEngine()

        after = engine.apply(BASE_STATE, Perturbation(node_drop=0.26))

        self.assertIsNot(after, BASE_STATE)
        self.assertEqual(BASE_STATE.nodes, (1, 2, 3, 4))
        self.assertEqual(BASE_STATE.edges, ((1, 2), (2, 3), (3, 4)))
        self.assertEqual(after.nodes, (1, 2, 3))
        self.assertEqual(after.edges, ((1, 2), (2, 3)))
        self.assertNotIn(4, after.features or {})
        self.assertNotIn(4, after.timestamps or {})


class OracleEngineTests(unittest.TestCase):
    def test_evaluate_transition_returns_deterministic_result_with_trace(self) -> None:
        engine = build_default_engine()
        after = PerturbationEngine().apply(BASE_STATE, Perturbation(cluster_split=True))

        first = engine.evaluate_transition(BASE_STATE, after)
        second = engine.evaluate_transition(BASE_STATE, after)

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.classification, "stable")
        self.assertEqual(first.trace["input_node_count"], 4)
        self.assertEqual(first.trace["output_edge_count"], 2)
        self.assertEqual(first.trace["policy_version"], first.policy_version)

    def test_evaluate_matches_transition_when_derived_after_is_identical(self) -> None:
        engine = build_default_engine()
        perturbation = Perturbation(cluster_split=True)
        after = PerturbationEngine().apply(BASE_STATE, perturbation)

        direct = engine.evaluate_transition(BASE_STATE, after)
        derived = engine.evaluate(BASE_STATE, perturbation)

        self.assertEqual(direct.to_dict(), derived.to_dict())

    def test_scan_preserves_input_order_and_result_count(self) -> None:
        engine = build_default_engine()
        perturbations = [
            Perturbation(node_drop=0.26),
            Perturbation(cluster_split=True),
            Perturbation(edge_drop=0.34),
        ]

        first = engine.scan(BASE_STATE, perturbations)
        second = engine.scan(BASE_STATE, perturbations)

        self.assertEqual(len(first), 3)
        self.assertEqual([result.to_dict() for result in first], [result.to_dict() for result in second])
        self.assertEqual(
            [result.trace["output_node_count"] for result in first],
            [3, 4, 4],
        )
        self.assertEqual(
            [result.trace["output_edge_count"] for result in first],
            [2, 2, 2],
        )

    def test_invalid_states_fail_with_explicit_exception(self) -> None:
        engine = build_default_engine()

        with self.assertRaises(OracleStateValidationError):
            engine.evaluate_transition({"nodes": [1], "edges": [[1, 2]]}, BASE_STATE)

        with self.assertRaises(OraclePerturbationError):
            engine.evaluate(BASE_STATE, {"node_drop": 1.2})

    def test_explanations_are_deterministic_and_non_empty(self) -> None:
        engine = build_default_engine()
        result = engine.evaluate(BASE_STATE, Perturbation(node_drop=0.51))

        first = explain_result(result)
        second = explain_result(result)

        self.assertEqual(result.classification, "marginal")
        self.assertEqual(first, second)
        self.assertTrue(first)


if __name__ == "__main__":
    unittest.main()
