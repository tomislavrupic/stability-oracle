from __future__ import annotations

import unittest

from haos_skill import POLICY_VERSION_V1, PolicyConfig, StabilityClassifier, StabilityMetrics


class ClassifierTests(unittest.TestCase):
    def test_stable_region_uses_floor_mean_band_policy(self) -> None:
        classifier = StabilityClassifier()
        result = classifier.evaluate(
            StabilityMetrics(
                structural_retention=0.9,
                temporal_consistency=0.85,
                causal_deformation=0.1,
                geometric_integrity=0.8,
            )
        )

        self.assertEqual(result.classification, "stable")
        self.assertEqual(result.policy_version, POLICY_VERSION_V1)
        self.assertEqual(result.normalized_vector["causal_stability"], 0.9)

    def test_floor_violation_is_unstable(self) -> None:
        classifier = StabilityClassifier()
        result = classifier.evaluate(
            StabilityMetrics(
                structural_retention=0.9,
                temporal_consistency=0.2,
                causal_deformation=0.1,
                geometric_integrity=0.9,
            )
        )

        self.assertEqual(result.classification, "unstable")

    def test_marginal_region_survives_without_stable_band(self) -> None:
        classifier = StabilityClassifier()
        result = classifier.evaluate(
            StabilityMetrics(
                structural_retention=0.6,
                temporal_consistency=0.62,
                causal_deformation=0.35,
                geometric_integrity=0.7,
            )
        )

        self.assertEqual(result.classification, "marginal")
        self.assertGreaterEqual(result.coherence_score, 0.5)

    def test_confidence_matches_coherence_times_inverse_spread(self) -> None:
        classifier = StabilityClassifier()
        result = classifier.evaluate(
            StabilityMetrics(
                structural_retention=0.8,
                temporal_consistency=0.8,
                causal_deformation=0.2,
                geometric_integrity=0.6,
            )
        )

        self.assertEqual(result.coherence_score, 0.75)
        self.assertEqual(result.confidence, 0.6)

    def test_policy_config_is_calibratable_without_code_changes(self) -> None:
        classifier = StabilityClassifier(
            PolicyConfig(
                floor_threshold=0.2,
                stable_coherence_threshold=0.8,
                stable_spread_threshold=0.2,
                marginal_coherence_threshold=0.45,
                policy_version="custom-v1",
            )
        )
        result = classifier.evaluate(
            StabilityMetrics(
                structural_retention=0.6,
                temporal_consistency=0.62,
                causal_deformation=0.35,
                geometric_integrity=0.7,
            )
        )

        self.assertEqual(result.classification, "marginal")
        self.assertEqual(result.policy_version, "custom-v1")


if __name__ == "__main__":
    unittest.main()
