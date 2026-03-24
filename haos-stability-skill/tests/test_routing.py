from __future__ import annotations

import unittest

from haos_skill import OracleRoute, Perturbation, RoutingContext, RoutingPolicy, route_candidate
from haos_skill.routing.router import OracleRouter, build_default_router


class _FakeLogicalEngine:
    def __init__(self) -> None:
        self.evaluate_calls: list[tuple[object, object]] = []
        self.transition_calls: list[tuple[object, object]] = []

    def evaluate(self, before: object, perturbation: object):
        self.evaluate_calls.append((before, perturbation))
        return _FakeOracleResult({"classification": "stable", "trace": {"path": "evaluate"}})

    def evaluate_transition(self, before: object, after: object):
        self.transition_calls.append((before, after))
        return _FakeOracleResult({"classification": "stable", "trace": {"path": "evaluate_transition"}})


class _FakeOracleResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return dict(self._payload)


class RoutingPolicyTests(unittest.TestCase):
    def test_explicit_foundational_requirement_routes_to_foundational(self) -> None:
        decision = RoutingPolicy().select(RoutingContext(requires_foundational_check=True))

        self.assertEqual(decision.selected_route, OracleRoute.FOUNDATIONAL)
        self.assertEqual(decision.confidence, 1.0)

    def test_explicit_structural_requirement_routes_to_logical(self) -> None:
        decision = RoutingPolicy().select(RoutingContext(requires_structural_stability=True))

        self.assertEqual(decision.selected_route, OracleRoute.LOGICAL)
        self.assertEqual(decision.confidence, 1.0)

    def test_explicit_empirical_requirement_routes_to_physical(self) -> None:
        decision = RoutingPolicy().select(RoutingContext(requires_empirical_search=True))

        self.assertEqual(decision.selected_route, OracleRoute.PHYSICAL)
        self.assertEqual(decision.confidence, 1.0)

    def test_domain_hints_map_correctly(self) -> None:
        policy = RoutingPolicy()
        cases = {
            "physical": OracleRoute.PHYSICAL,
            "logical": OracleRoute.LOGICAL,
            "foundational": OracleRoute.FOUNDATIONAL,
        }

        for domain_hint, expected in cases.items():
            with self.subTest(domain_hint=domain_hint):
                decision = policy.select(RoutingContext(domain_hint=domain_hint))
                self.assertEqual(decision.selected_route, expected)
                self.assertEqual(decision.confidence, 0.8)

    def test_unknown_inputs_route_to_unknown(self) -> None:
        decision = RoutingPolicy().select(RoutingContext())

        self.assertEqual(decision.selected_route, OracleRoute.UNKNOWN)
        self.assertEqual(decision.confidence, 0.4)

    def test_unknown_domain_hint_routes_to_unknown_with_documented_confidence(self) -> None:
        decision = RoutingPolicy().select(RoutingContext(domain_hint="symbolic"))

        self.assertEqual(decision.selected_route, OracleRoute.UNKNOWN)
        self.assertEqual(decision.confidence, 0.4)
        self.assertEqual(decision.rationale, "unknown_domain_hint:symbolic")


class OracleRouterTests(unittest.TestCase):
    def test_logical_dispatch_reaches_logical_engine(self) -> None:
        logical_engine = _FakeLogicalEngine()
        router = OracleRouter(policy=RoutingPolicy(), logical_engine=logical_engine)

        result = router.dispatch(
            RoutingContext(requires_structural_stability=True),
            before={"nodes": [1], "edges": []},
            perturbation=Perturbation(),
        )

        self.assertEqual(result.status, "ok")
        self.assertTrue(result.implemented)
        self.assertEqual(result.route, OracleRoute.LOGICAL)
        self.assertEqual(len(logical_engine.evaluate_calls), 1)
        self.assertEqual(result.result, {"classification": "stable", "trace": {"path": "evaluate"}})

    def test_physical_dispatch_returns_stub(self) -> None:
        router = OracleRouter(policy=RoutingPolicy(), logical_engine=None)

        result = router.dispatch(RoutingContext(requires_empirical_search=True))

        self.assertEqual(result.status, "stub")
        self.assertFalse(result.implemented)
        self.assertEqual(result.route, OracleRoute.PHYSICAL)

    def test_foundational_dispatch_returns_stub(self) -> None:
        router = OracleRouter(policy=RoutingPolicy(), logical_engine=None)

        result = router.dispatch(RoutingContext(requires_foundational_check=True))

        self.assertEqual(result.status, "stub")
        self.assertFalse(result.implemented)
        self.assertEqual(result.route, OracleRoute.FOUNDATIONAL)

    def test_router_never_crashes_on_missing_optional_fields(self) -> None:
        router = OracleRouter(policy=RoutingPolicy(), logical_engine=None)

        decision = router.decide(RoutingContext())
        dispatch = router.dispatch(RoutingContext())

        self.assertEqual(decision.selected_route, OracleRoute.UNKNOWN)
        self.assertEqual(dispatch.status, "stub")
        self.assertEqual(dispatch.route, OracleRoute.UNKNOWN)

    def test_route_candidate_helper_dispatches_with_default_router(self) -> None:
        before = {
            "nodes": [1, 2, 3, 4],
            "edges": [[1, 2], [2, 3], [3, 4]],
            "timestamps": {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0},
        }
        result = route_candidate(
            RoutingContext(requires_structural_stability=True),
            before=before,
            perturbation=Perturbation(cluster_split=True),
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.route, OracleRoute.LOGICAL)
        self.assertIn("trace", result.result or {})

    def test_build_default_router_provides_logical_engine(self) -> None:
        router = build_default_router()

        self.assertIsNotNone(router.logical_engine)


if __name__ == "__main__":
    unittest.main()
