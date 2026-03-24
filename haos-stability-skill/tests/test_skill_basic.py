from __future__ import annotations

import unittest
from unittest.mock import patch

from haos_skill import evaluate_structure, scan_structure
from haos_skill.adapter import NormalizedOracleMetrics


SAMPLE_STATE = {
    "plan_id": "baseline",
    "nodes": [{"id": "a"}, {"id": "b"}],
    "edges": [{"source": "a", "target": "b"}],
}


class SkillBasicTests(unittest.TestCase):
    def test_evaluate_structure_returns_bounded_report(self) -> None:
        metrics = NormalizedOracleMetrics(
            structural_retention=0.92,
            temporal_consistency=0.95,
            causal_deformation=0.10,
            geometric_integrity=0.93,
            classification_hint=None,
            primary_reason=None,
        )

        with patch("haos_skill.skill.run_stability_oracle", return_value=metrics):
            report = evaluate_structure(SAMPLE_STATE, timeout=1.5)

        self.assertEqual(report["classification"], "stable")
        self.assertEqual(report["policy_version"], "v1_floor_mean_band")
        self.assertIn("summary", report)
        self.assertIn("confidence", report)
        self.assertIn("coherence_score", report)
        self.assertIn("metric_vector", report)
        self.assertIn("normalized_vector", report)
        self.assertLessEqual(report["causal_deformation"], 1.0)

    def test_scan_structure_returns_counts(self) -> None:
        metrics = NormalizedOracleMetrics(
            structural_retention=0.35,
            temporal_consistency=0.50,
            causal_deformation=0.85,
            geometric_integrity=0.40,
            classification_hint=None,
            primary_reason=None,
        )

        with patch("haos_skill.skill.run_stability_oracle", return_value=metrics):
            result = scan_structure(
                {
                    "cases": [
                        {"case_id": "fragile-1", "state_spec": SAMPLE_STATE},
                        {"case_id": "fragile-2", "state_spec": SAMPLE_STATE},
                    ]
                }
            )

        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["counts"]["unstable"], 2)
        self.assertEqual(result["counts"]["stable"], 0)

    def test_local_policy_owns_classification_even_if_adapter_supplies_hint(self) -> None:
        metrics = NormalizedOracleMetrics(
            structural_retention=0.15,
            temporal_consistency=0.2,
            causal_deformation=0.1,
            geometric_integrity=0.9,
            classification_hint="stable",
            primary_reason=None,
        )

        with patch("haos_skill.skill.run_stability_oracle", return_value=metrics):
            report = evaluate_structure(SAMPLE_STATE)

        self.assertEqual(report["classification"], "unstable")

    def test_external_sentence_summary_is_not_wrapped_twice(self) -> None:
        metrics = NormalizedOracleMetrics(
            structural_retention=0.92,
            temporal_consistency=0.95,
            causal_deformation=0.10,
            geometric_integrity=0.93,
            classification_hint="stable",
            primary_reason="Structure is stable with clean propagation and retained invariants.",
        )

        with patch("haos_skill.skill.run_stability_oracle", return_value=metrics):
            report = evaluate_structure(SAMPLE_STATE)

        self.assertEqual(
            report["summary"],
            "Structure is stable with clean propagation and retained invariants.",
        )


if __name__ == "__main__":
    unittest.main()
