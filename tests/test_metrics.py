from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from oracle.metrics_persistence import compute_persistence_metrics
from oracle.metrics_propagation import compute_propagation_metrics
from oracle.report import scan_trajectory
from oracle.trajectory import TrajectoryValidationError, load_trajectory_file


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class StabilityOracleTests(unittest.TestCase):
    def test_stable_plan_scores_higher_than_fragile_plan(self) -> None:
        stable = load_trajectory_file(EXAMPLES / "media_pipeline_plan.json")
        fragile = load_trajectory_file(EXAMPLES / "fragile_plan.json")

        stable_propagation = compute_propagation_metrics(stable)
        fragile_propagation = compute_propagation_metrics(fragile)
        stable_persistence = compute_persistence_metrics(stable)
        fragile_persistence = compute_persistence_metrics(fragile)

        self.assertGreater(stable_propagation.score, fragile_propagation.score)
        self.assertGreater(stable_persistence.score, fragile_persistence.score)

    def test_classifier_marks_stable_green_and_fragile_red(self) -> None:
        stable_report = scan_trajectory(load_trajectory_file(EXAMPLES / "media_pipeline_plan.json"))
        fragile_report = scan_trajectory(load_trajectory_file(EXAMPLES / "fragile_plan.json"))

        self.assertEqual(stable_report.classification.label, "green")
        self.assertEqual(fragile_report.classification.label, "red")

    def test_validation_rejects_missing_edge_endpoint(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write(
                """
{
  "plan_id": "broken",
  "nodes": [
    {
      "id": "start",
      "step_type": "input",
      "reversible": true,
      "checkpoint": true,
      "invariant_tags": ["source"],
      "risk_weight": 0.1
    }
  ],
  "edges": [
    { "source": "start", "target": "missing" }
  ]
}
""".strip()
            )
            broken_payload = Path(handle.name)
        self.addCleanup(lambda: broken_payload.unlink(missing_ok=True))

        with self.assertRaises(TrajectoryValidationError):
            load_trajectory_file(broken_payload)


if __name__ == "__main__":
    unittest.main()
