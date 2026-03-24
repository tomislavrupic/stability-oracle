from __future__ import annotations

from pathlib import Path
import time
import unittest
from unittest.mock import patch

from haos_iip_skill import SkillTimeoutError, evaluate_structure, load_schema, scan_structure
from oracle.report import scan_trajectory
from oracle.trajectory import load_trajectory_file


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class HAOSIIPSkillTests(unittest.TestCase):
    def test_evaluate_structure_returns_bounded_contract(self) -> None:
        stable_spec = load_trajectory_file(EXAMPLES / "media_pipeline_plan.json")

        result = evaluate_structure(stable_spec)

        self.assertEqual(result["classification"], "stable")
        for key in (
            "structural_retention",
            "temporal_consistency",
            "causal_deformation",
            "geometric_integrity",
        ):
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)
        self.assertIn("summary", result)

    def test_evaluate_structure_maps_fragile_plan_to_unstable(self) -> None:
        fragile_spec = load_trajectory_file(EXAMPLES / "fragile_plan.json")

        result = evaluate_structure(fragile_spec)

        self.assertEqual(result["classification"], "unstable")

    def test_scan_structure_returns_case_map(self) -> None:
        stable_spec = load_trajectory_file(EXAMPLES / "media_pipeline_plan.json").to_dict()
        fragile_spec = load_trajectory_file(EXAMPLES / "fragile_plan.json").to_dict()

        stability_map = scan_structure(
            {
                "cases": [
                    {"case_id": "stable-case", "state_spec": stable_spec},
                    {"case_id": "fragile-case", "state_spec": fragile_spec},
                ]
            }
        )

        self.assertEqual(stability_map["case_count"], 2)
        self.assertEqual(stability_map["counts"]["stable"], 1)
        self.assertEqual(stability_map["counts"]["unstable"], 1)
        self.assertEqual(stability_map["counts"]["marginal"], 0)

    def test_schema_exposes_expected_tools(self) -> None:
        schema = load_schema()

        self.assertEqual(schema["skill_name"], "haos_iip_skill")
        self.assertEqual([tool["name"] for tool in schema["tools"]], ["evaluate_structure", "scan_structure"])

    def test_timeout_guard_raises(self) -> None:
        stable_spec = load_trajectory_file(EXAMPLES / "media_pipeline_plan.json")

        def slow_evaluate(spec):
            time.sleep(0.05)
            return scan_trajectory(spec)

        with patch("haos_iip_skill.skill._evaluate_spec", side_effect=slow_evaluate):
            with self.assertRaises(SkillTimeoutError):
                evaluate_structure(stable_spec, timeout_seconds=0.01)


if __name__ == "__main__":
    unittest.main()
