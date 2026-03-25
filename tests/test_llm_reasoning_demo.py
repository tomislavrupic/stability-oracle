from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
HAOS_SKILL_ROOT = ROOT / "haos-stability-skill"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HAOS_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(HAOS_SKILL_ROOT))

from stability_oracle_demo.pipeline.demo_runner import EXPLANATIONS_PATH, ReasoningTraceOracle, run_demo
from stability_oracle_demo.telemetry.adapters.llm_reasoning_adapter import LLMReasoningAdapter, VECTOR_KEYS


DATASET_PATH = ROOT / "stability_oracle_demo" / "data" / "reasoning_demo_traces.json"


class LLMReasoningDemoTests(unittest.TestCase):
    def test_adapter_emits_fixed_eight_dimensional_vectors(self) -> None:
        trace = [
            {"step_index": 0, "text": "Add 14 and 9. 14 + 9 = 23.", "is_final": False},
            {"step_index": 1, "text": "The computation stays 23, so the result is consistent.", "is_final": False},
            {"step_index": 2, "text": "Final answer: 23.", "is_final": True},
        ]

        sequence = LLMReasoningAdapter().from_trace(trace, "demo-trace")

        self.assertEqual(len(sequence.frames), 3)
        for frame in sequence.frames:
            self.assertEqual(len(frame.state_vector), 8)
            self.assertEqual(frame.metadata["vector_keys"], list(VECTOR_KEYS))
            for value in frame.state_vector:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_demo_runner_separates_trace_types(self) -> None:
        frame = run_demo(DATASET_PATH)

        counts = frame.groupby(["trace_type", "oracle_class"]).size().to_dict()

        self.assertEqual(counts.get(("coherent", "stable")), 4)
        self.assertEqual(counts.get(("drifted", "marginal")), 4)
        self.assertEqual(counts.get(("broken", "unstable")), 4)

        explanations = json.loads(EXPLANATIONS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(explanations), 12)
        self.assertIn("dominant_metric_contribution", explanations[0])
        self.assertIn("transition_magnitude", explanations[0])
        self.assertIn("recovery_score_trend", explanations[0])
        self.assertIn("final_class_reason", explanations[0])

    def test_noisy_return_trace_is_not_classified_as_broken(self) -> None:
        trace = [
            {"step_index": 0, "text": "Add 12 and 8. 12 + 8 = 20.", "is_final": False},
            {
                "step_index": 1,
                "text": "Wait, maybe subtraction matters, but 20 is still the current candidate answer.",
                "is_final": False,
            },
            {"step_index": 2, "text": "The addition path returns: 12 + 8 = 20.", "is_final": False},
            {"step_index": 3, "text": "Final answer: 20.", "is_final": True},
        ]

        sequence = LLMReasoningAdapter().from_trace(trace, "edge-return")
        result = ReasoningTraceOracle().classify(sequence)

        self.assertEqual(result["class"], "marginal")


if __name__ == "__main__":
    unittest.main()
