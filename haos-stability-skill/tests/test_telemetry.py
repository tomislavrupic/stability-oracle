from __future__ import annotations

import math
import unittest

from haos_skill import (
    GeometryEncoderConfig,
    HaosTelemetryAdapter,
    InvalidTelemetry,
    Perturbation,
    State,
    StateGeometryEncoder,
    TelemetryBridgeError,
    TelemetryFrame,
    TelemetrySequence,
    TemporalNormalizer,
    TemporalNormalizerConfig,
    build_default_engine,
    telemetry_to_state_transition,
)
from haos_skill.perturbations import PerturbationEngine


BASE_STATE = State(
    nodes=(1, 2, 3, 4),
    edges=((1, 2), (2, 3), (3, 4)),
    features={4: {"kind": "sink"}},
    timestamps={1: 0.0, 2: 1.0, 3: 2.0, 4: 3.0},
)


class TelemetryContractTests(unittest.TestCase):
    def test_frame_rejects_non_finite_timestamp_or_values(self) -> None:
        with self.assertRaises(InvalidTelemetry):
            TelemetryFrame(timestamp=float("nan"), entity_id="demo", state_vector=(1.0,))

        with self.assertRaises(InvalidTelemetry):
            TelemetryFrame(timestamp=0.0, entity_id="demo", state_vector=(1.0, float("inf")))

    def test_sequence_rejects_inconsistent_feature_width(self) -> None:
        with self.assertRaises(InvalidTelemetry):
            TelemetrySequence(
                frames=(
                    TelemetryFrame(timestamp=0.0, entity_id="demo", state_vector=(1.0, 2.0)),
                    TelemetryFrame(timestamp=1.0, entity_id="demo", state_vector=(1.0,)),
                ),
                entity_id="demo",
                feature_dim=2,
            )

    def test_sequence_rejects_decreasing_timestamps(self) -> None:
        with self.assertRaises(InvalidTelemetry):
            TelemetrySequence(
                frames=(
                    TelemetryFrame(timestamp=1.0, entity_id="demo", state_vector=(1.0,)),
                    TelemetryFrame(timestamp=0.0, entity_id="demo", state_vector=(2.0,)),
                ),
                entity_id="demo",
                feature_dim=1,
            )


class HaosTelemetryAdapterTests(unittest.TestCase):
    def test_adapter_emits_valid_two_frame_sequence(self) -> None:
        adapter = HaosTelemetryAdapter()
        after = PerturbationEngine().apply(BASE_STATE, Perturbation(cluster_split=True))

        sequence = adapter.from_state_pair(BASE_STATE, after)

        self.assertEqual(sequence.entity_id, "haos-transition")
        self.assertEqual(len(sequence.frames), 2)
        self.assertEqual(sequence.feature_dim, len(sequence.frames[0].state_vector))
        self.assertEqual(sequence.metadata["adapter"], "haos_state_pair_v1")
        self.assertIn("bridge_state_transition", sequence.metadata)


class TelemetryPipelineTests(unittest.TestCase):
    def test_normalizer_default_path_is_deterministic_and_preserves_width(self) -> None:
        adapter = HaosTelemetryAdapter()
        after = PerturbationEngine().apply(BASE_STATE, Perturbation(cluster_split=True))
        sequence = adapter.from_state_pair(BASE_STATE, after)
        normalizer = TemporalNormalizer()

        first = normalizer.normalize(sequence)
        second = normalizer.normalize(sequence)

        self.assertEqual(first, second)
        self.assertEqual(first.feature_dim, sequence.feature_dim)

    def test_geometry_encoder_default_path_is_deterministic(self) -> None:
        adapter = HaosTelemetryAdapter()
        after = PerturbationEngine().apply(BASE_STATE, Perturbation(cluster_split=True))
        sequence = adapter.from_state_pair(BASE_STATE, after)
        encoder = StateGeometryEncoder()

        first = encoder.encode(sequence)
        second = encoder.encode(sequence)

        self.assertEqual(first, second)
        self.assertGreater(first.feature_dim, sequence.feature_dim)

    def test_bridge_fails_closed_on_invalid_shape(self) -> None:
        sequence = TelemetrySequence(
            frames=(
                TelemetryFrame(timestamp=0.0, entity_id="demo", state_vector=(1.0, 2.0)),
            ),
            entity_id="demo",
            feature_dim=2,
            metadata={"adapter": "haos_state_pair_v1"},
        )

        with self.assertRaises(TelemetryBridgeError):
            telemetry_to_state_transition(sequence)

    def test_haos_adapter_pipeline_matches_logical_oracle_verdict(self) -> None:
        engine = build_default_engine()
        adapter = HaosTelemetryAdapter()
        normalizer = TemporalNormalizer()
        encoder = StateGeometryEncoder()

        cases = (
            ("stable", Perturbation(cluster_split=True)),
            ("marginal", Perturbation(node_drop=0.51)),
            ("unstable", Perturbation(node_drop=0.76)),
        )

        for expected_classification, perturbation in cases:
            with self.subTest(expected_classification=expected_classification):
                after = PerturbationEngine().apply(BASE_STATE, perturbation)
                direct = engine.evaluate_transition(BASE_STATE, after)

                sequence = adapter.from_state_pair(BASE_STATE, after)
                normalized = normalizer.normalize(sequence)
                encoded = encoder.encode(normalized)
                before_payload, after_payload = telemetry_to_state_transition(encoded)
                bridged = engine.evaluate_transition(before_payload, after_payload)

                self.assertEqual(direct.classification, expected_classification)
                self.assertEqual(bridged.classification, direct.classification)


if __name__ == "__main__":
    unittest.main()
