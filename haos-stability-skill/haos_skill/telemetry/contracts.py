from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from typing import Any, Dict, Mapping, Sequence


class InvalidTelemetry(ValueError):
    """Raised when telemetry violates the bounded contract."""


@dataclass(frozen=True)
class TelemetryFrame:
    """
    Minimal domain-agnostic telemetry atom.

    - timestamp: absolute or relative scalar time
    - entity_id: source identity
    - state_vector: numeric feature vector
    - metadata: optional non-numeric annotations
    """

    timestamp: float
    entity_id: str | int
    state_vector: Sequence[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        timestamp = _coerce_finite_float(self.timestamp, "timestamp")
        entity_id = _normalize_entity_id(self.entity_id)
        state_vector = _normalize_state_vector(self.state_vector)
        metadata = _normalize_metadata(self.metadata, "metadata")

        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "entity_id", entity_id)
        object.__setattr__(self, "state_vector", state_vector)
        object.__setattr__(self, "metadata", metadata)

        validate_frame(self)


@dataclass(frozen=True)
class TelemetrySequence:
    """
    Ordered telemetry stream for one assessment unit.

    Contract:
    - frames must be sorted by timestamp
    - all frames in one normalized assessment stream must share fixed width
    - entity_id must be consistent unless explicitly multi-entity
    """

    frames: tuple[TelemetryFrame, ...]
    entity_id: str | int
    feature_dim: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.frames, Sequence) or isinstance(self.frames, (str, bytes, bytearray)):
            raise InvalidTelemetry("frames must be a sequence of TelemetryFrame")
        normalized_frames = tuple(_coerce_frame(frame) for frame in self.frames)
        entity_id = _normalize_entity_id(self.entity_id)
        feature_dim = _normalize_feature_dim(self.feature_dim)
        metadata = _normalize_metadata(self.metadata, "metadata")

        object.__setattr__(self, "frames", normalized_frames)
        object.__setattr__(self, "entity_id", entity_id)
        object.__setattr__(self, "feature_dim", feature_dim)
        object.__setattr__(self, "metadata", metadata)

        validate_sequence(self)


def validate_frame(frame: TelemetryFrame) -> None:
    if not math.isfinite(frame.timestamp):
        raise InvalidTelemetry("frame timestamp must be finite")
    if not frame.state_vector:
        raise InvalidTelemetry("frame state_vector must contain at least one numeric value")
    for value in frame.state_vector:
        if not math.isfinite(value):
            raise InvalidTelemetry("frame state_vector must contain only finite numeric values")


def validate_sequence(seq: TelemetrySequence) -> None:
    if not seq.frames:
        raise InvalidTelemetry("sequence must contain at least one frame")
    if seq.feature_dim <= 0:
        raise InvalidTelemetry("feature_dim must be greater than zero")

    expected_entity_id = seq.entity_id
    previous_timestamp = None
    for frame in seq.frames:
        validate_frame(frame)
        if frame.entity_id != expected_entity_id:
            raise InvalidTelemetry("all frames in a sequence must share one entity_id")
        if len(frame.state_vector) != seq.feature_dim:
            raise InvalidTelemetry("all frames in a sequence must share fixed feature width")
        if previous_timestamp is not None and frame.timestamp < previous_timestamp:
            raise InvalidTelemetry("frame timestamps must be nondecreasing")
        previous_timestamp = frame.timestamp


def _coerce_frame(value: Any) -> TelemetryFrame:
    if not isinstance(value, TelemetryFrame):
        raise InvalidTelemetry("frames must contain TelemetryFrame instances")
    return value


def _normalize_entity_id(value: Any) -> str | int:
    if isinstance(value, bool):
        raise InvalidTelemetry("entity_id cannot be a boolean")
    if isinstance(value, int):
        return value
    normalized = str(value).strip()
    if not normalized:
        raise InvalidTelemetry("entity_id must be a non-empty string or integer")
    return normalized


def _normalize_state_vector(value: Sequence[float]) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise InvalidTelemetry("state_vector must be a sequence of numeric values")
    normalized = tuple(_coerce_finite_float(item, "state_vector") for item in value)
    if not normalized:
        raise InvalidTelemetry("state_vector must contain at least one numeric value")
    return normalized


def _normalize_feature_dim(value: Any) -> int:
    if isinstance(value, bool):
        raise InvalidTelemetry("feature_dim must be an integer")
    normalized = int(value)
    if normalized <= 0:
        raise InvalidTelemetry("feature_dim must be greater than zero")
    return normalized


def _normalize_metadata(value: Any, field_name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise InvalidTelemetry("%s must be a mapping" % field_name)
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True, ensure_ascii=True))
    except (TypeError, ValueError) as exc:
        raise InvalidTelemetry("%s must be JSON-serializable" % field_name) from exc
    if not isinstance(normalized, dict):
        raise InvalidTelemetry("%s must serialize to a JSON object" % field_name)
    return normalized


def _coerce_finite_float(value: Any, field_name: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidTelemetry("%s must be numeric" % field_name) from exc
    if not math.isfinite(numeric):
        raise InvalidTelemetry("%s must be finite" % field_name)
    return round(numeric, 6)
