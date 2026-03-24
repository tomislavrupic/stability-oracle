from __future__ import annotations

import unittest
from unittest.mock import patch

from haos_skill import DeterministicHashCache, evaluate_structure
from haos_skill.adapter import NormalizedOracleMetrics


STATE_A = {
    "plan_id": "ordered-a",
    "nodes": [{"id": "a"}, {"id": "b"}],
    "edges": [{"source": "a", "target": "b"}],
}

STATE_B = {
    "edges": [{"target": "b", "source": "a"}],
    "nodes": [{"id": "a"}, {"id": "b"}],
    "plan_id": "ordered-a",
}


class DeterminismTests(unittest.TestCase):
    def test_cache_key_is_stable_for_equivalent_payloads(self) -> None:
        cache = DeterministicHashCache()
        metrics = NormalizedOracleMetrics(
            structural_retention=0.88,
            temporal_consistency=0.91,
            causal_deformation=0.14,
            geometric_integrity=0.90,
            classification_hint="stable",
            primary_reason="external classification",
        )

        with patch("haos_skill.skill.run_stability_oracle", return_value=metrics) as mocked:
            first = evaluate_structure(STATE_A, cache=cache, oracle_command=("mock-oracle",))
            second = evaluate_structure(STATE_B, cache=cache, oracle_command=("mock-oracle",))

        self.assertEqual(first, second)
        self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
