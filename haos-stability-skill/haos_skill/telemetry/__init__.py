"""Parallel telemetry layer for trajectory ingestion."""

from .adapters import HaosTelemetryAdapter, HaosTelemetryAdapterConfig
from .bridge import TelemetryBridgeError, telemetry_to_state_transition
from .contracts import InvalidTelemetry, TelemetryFrame, TelemetrySequence, validate_frame, validate_sequence
from .geometry import GeometryEncoderConfig, StateGeometryEncoder
from .normalizer import TemporalNormalizer, TemporalNormalizerConfig

__all__ = [
    "GeometryEncoderConfig",
    "HaosTelemetryAdapter",
    "HaosTelemetryAdapterConfig",
    "InvalidTelemetry",
    "StateGeometryEncoder",
    "TelemetryBridgeError",
    "TelemetryFrame",
    "TelemetrySequence",
    "TemporalNormalizer",
    "TemporalNormalizerConfig",
    "telemetry_to_state_transition",
    "validate_frame",
    "validate_sequence",
]
