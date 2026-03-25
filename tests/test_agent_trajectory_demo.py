from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
HAOS_SKILL_ROOT = ROOT / "haos-stability-skill"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HAOS_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(HAOS_SKILL_ROOT))

from stability_oracle_demo_agent.pipeline.demo_runner import run_demo
from stability_oracle_demo_agent.simulator.generator import dataset_payload, generate_dataset_records
from stability_oracle_demo_agent.telemetry.adapters.agent_trajectory_adapter import AgentTrajectoryAdapter
from haos_skill import StateGeometryEncoder, TemporalNormalizer, build_default_engine, telemetry_to_state_transition


DATASET_PATH = ROOT / "stability_oracle_demo_agent" / "data" / "agent_traces.json"


class AgentTrajectoryDemoTests(unittest.TestCase):
    def test_dataset_generation_is_deterministic(self) -> None:
        first = dataset_payload()
        second = dataset_payload()
        self.assertEqual(first, second)
        self.assertEqual(first["trajectory_count"], 15)

    def test_adapter_emits_fixed_eight_dimensional_vectors(self) -> None:
        trajectory = generate_dataset_records(per_regime=1)[0]
        sequence = AgentTrajectoryAdapter().from_trajectory(trajectory, trajectory["trajectory_id"])

        self.assertEqual(sequence.feature_dim, 8)
        self.assertEqual(len(sequence.frames), 100)
        for frame in sequence.frames:
            self.assertEqual(len(frame.state_vector), 8)
            for value in frame.state_vector:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_regime_examples_classify_into_expected_bands(self) -> None:
        trajectories = generate_dataset_records(per_regime=1)
        adapter = AgentTrajectoryAdapter()
        normalizer = TemporalNormalizer()
        encoder = StateGeometryEncoder()
        engine = build_default_engine()

        verdicts: dict[str, str] = {}
        for trajectory in trajectories:
            sequence = adapter.from_trajectory(trajectory, trajectory["trajectory_id"])
            sequence = normalizer.normalize(sequence)
            sequence = encoder.encode(sequence)
            before, after = telemetry_to_state_transition(sequence)
            result = engine.evaluate_transition(before, after)
            verdicts[trajectory["regime_label"]] = result.classification

        self.assertEqual(verdicts["stable"], "stable")
        self.assertEqual(verdicts["unstable"], "unstable")
        self.assertEqual(verdicts["marginal"], "marginal")

    def test_demo_runner_separates_dataset(self) -> None:
        frame = run_demo(DATASET_PATH)
        counts = frame.groupby(["regime_label", "oracle_class"]).size().to_dict()

        self.assertEqual(counts.get(("stable", "stable")), 5)
        self.assertEqual(counts.get(("marginal", "marginal")), 5)
        self.assertEqual(counts.get(("unstable", "unstable")), 5)


if __name__ == "__main__":
    unittest.main()
